"""Graph-based memory store with hybrid vector + graph search."""

import json
import logging

from app.services import store
from app.services.memory.vector_store import embed

logger = logging.getLogger(__name__)

HYBRID_ALPHA = 0.7  # weight for vector similarity vs graph proximity


def insert_node(
    label: str,
    node_type: str,
    content: str,
    metadata: dict | None = None,
    source_conversation_id: str | None = None,
) -> str:
    """Embed content and upsert a memory node."""
    embedding = embed(content)
    return store.upsert_memory_node(
        label=label, node_type=node_type, content=content,
        embedding=embedding, metadata=metadata,
        source_conversation_id=source_conversation_id,
    )


def insert_edge(
    source_id: str, target_id: str, relation_type: str,
    weight: float = 1.0, metadata: dict | None = None,
) -> str:
    return store.insert_memory_edge(
        source_id=source_id, target_id=target_id,
        relation_type=relation_type, weight=weight, metadata=metadata,
    )


def search_nodes(
    query: str, limit: int = 10, threshold: float = 0.5,
    node_types: list[str] | None = None,
) -> list[dict]:
    """Vector similarity search on memory nodes."""
    embedding = embed(query)
    return store.search_memory_nodes(
        embedding=embedding, limit=limit, threshold=threshold,
        node_types=node_types,
    )


def get_neighbors(node_id: str, depth: int = 2, max_nodes: int = 20) -> list[dict]:
    """BFS graph traversal from a node up to `depth` hops."""
    visited = {node_id}
    frontier = [node_id]
    results = []

    for d in range(depth):
        if not frontier or len(results) >= max_nodes:
            break
        neighbors = store.get_memory_node_neighbors(frontier)
        next_frontier = []
        for item in neighbors:
            nid = item["node"]["id"]
            if nid not in visited:
                visited.add(nid)
                item["depth"] = d + 1
                results.append(item)
                next_frontier.append(nid)
                if len(results) >= max_nodes:
                    break
        frontier = next_frontier

    return results


def hybrid_search(
    query: str,
    limit: int = 5,
    threshold: float = 0.5,
    graph_depth: int = 2,
    max_total: int = 15,
) -> list[dict]:
    """Hybrid search: vector similarity + graph expansion + combined ranking."""
    # 1. Vector search for seed nodes
    seeds = search_nodes(query, limit=limit, threshold=threshold)
    if not seeds:
        return []

    # Build result map: node_id -> {node, score}
    result_map: dict[str, dict] = {}
    for s in seeds:
        result_map[s["id"]] = {
            "node": s,
            "vector_similarity": s.get("similarity", 0),
            "graph_depth": 0,
            "source": "vector",
        }

    # 2. Graph expansion from seed nodes
    seed_ids = [s["id"] for s in seeds]
    for seed_id in seed_ids:
        neighbors = get_neighbors(seed_id, depth=graph_depth, max_nodes=max_total)
        for item in neighbors:
            nid = item["node"]["id"]
            depth = item["depth"]
            if nid not in result_map:
                result_map[nid] = {
                    "node": item["node"],
                    "vector_similarity": 0,
                    "graph_depth": depth,
                    "edge": item.get("edge"),
                    "source": "graph",
                }
            else:
                # Node found by both vector and graph — mark as hybrid
                existing = result_map[nid]
                existing["source"] = "hybrid"
                existing["graph_depth"] = min(existing["graph_depth"], depth)

    # 3. Score and rank
    ranked = []
    for nid, info in result_map.items():
        vec_score = info["vector_similarity"]
        graph_score = 1.0 / (1 + info["graph_depth"]) if info["graph_depth"] > 0 else 0
        # Hybrid bonus: nodes found by both get a boost
        hybrid_bonus = 0.1 if info["source"] == "hybrid" else 0
        final_score = HYBRID_ALPHA * vec_score + (1 - HYBRID_ALPHA) * graph_score + hybrid_bonus
        ranked.append({
            "id": nid,
            "content": info["node"].get("content", ""),
            "label": info["node"].get("label", ""),
            "node_type": info["node"].get("node_type", ""),
            "score": final_score,
            "source": info["source"],
            "edge": info.get("edge"),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:max_total]


def extract_and_store_graph_memories(
    messages: list[dict],
    conversation_id: str,
    llm_generate_fn=None,
) -> list[str]:
    """Use LLM to extract entities, facts, and relationships, then store as graph nodes+edges."""
    from app.services.providers.base import ChatMessage, LLMRequest

    if not messages or not llm_generate_fn:
        return []

    recent = messages[-10:]
    conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    extraction_prompt = (
        "Extract entities, facts, and relationships from this conversation.\n"
        "Return ONLY valid JSON (no markdown fences) in this exact format:\n"
        '{"nodes": [{"label": "short name", "type": "entity|concept|fact", '
        '"content": "detailed description"}], '
        '"edges": [{"source_label": "...", "target_label": "...", '
        '"relation": "related_to|part_of|preference_of|precedes|contradicts"}]}\n'
        "Rules:\n"
        "- Only include concrete, memorable information\n"
        "- Labels should be short, reusable identifiers (e.g. 'Python', 'user preference: dark mode')\n"
        "- If nothing notable, return {\"nodes\": [], \"edges\": []}"
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=conversation_text)],
        system_prompt=extraction_prompt,
        temperature=0.3,
        max_tokens=1024,
    )

    try:
        response = llm_generate_fn(req)
        raw = response.reply_text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        if not nodes:
            return []

        # Insert nodes, collect label->id mapping
        label_to_id: dict[str, str] = {}
        node_ids: list[str] = []
        for n in nodes:
            label = n.get("label", "").strip()
            ntype = n.get("type", "fact")
            content = n.get("content", label)
            if not label:
                continue
            nid = insert_node(
                label=label, node_type=ntype, content=content,
                source_conversation_id=conversation_id,
            )
            label_to_id[label] = nid
            node_ids.append(nid)

        # Insert edges
        for e in edges:
            src_label = e.get("source_label", "").strip()
            tgt_label = e.get("target_label", "").strip()
            relation = e.get("relation", "related_to")
            src_id = label_to_id.get(src_label)
            tgt_id = label_to_id.get(tgt_label)
            if src_id and tgt_id and src_id != tgt_id:
                try:
                    insert_edge(src_id, tgt_id, relation)
                except Exception as edge_err:
                    logger.debug("Failed to insert edge %s->%s: %s", src_label, tgt_label, edge_err)

        logger.info("Extracted %d nodes and %d edges from conversation %s",
                     len(node_ids), len(edges), conversation_id)
        return node_ids

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse graph extraction response: %s", e)
        return []
    except Exception as e:
        logger.warning("Graph memory extraction failed: %s", e)
        return []
