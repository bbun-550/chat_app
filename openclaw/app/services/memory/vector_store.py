import logging
import os

from sentence_transformers import SentenceTransformer

from app.services import store

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed(text: str) -> list[float]:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def store_memory(
    content: str,
    memory_type: str = "fact",
    source_conversation_id: str | None = None,
) -> str:
    embedding = embed(content)
    return store.insert_vector_memory(
        content=content,
        embedding=embedding,
        memory_type=memory_type,
        source_conversation_id=source_conversation_id,
    )


def search(query: str, limit: int = 5, threshold: float = 0.7) -> list[dict]:
    embedding = embed(query)
    return store.search_vector_memories(
        embedding=embedding, limit=limit, threshold=threshold,
    )


def extract_and_store_memories(
    messages: list[dict],
    conversation_id: str,
    llm_generate_fn=None,
) -> list[str]:
    """Extract memorable facts from messages and store them.

    If llm_generate_fn is provided, uses LLM to extract facts.
    Otherwise, stores the last assistant message as a fact.
    """
    from app.services.providers.base import ChatMessage, LLMRequest

    if not messages:
        return []

    if llm_generate_fn:
        recent = messages[-10:]
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in recent
        )
        extraction_prompt = (
            "Extract important facts, preferences, or knowledge from this conversation. "
            "Return each fact on a new line. Only include concrete, memorable information. "
            "If there are no notable facts, return 'NONE'."
        )
        req = LLMRequest(
            messages=[ChatMessage(role="user", content=conversation_text)],
            system_prompt=extraction_prompt,
            temperature=0.3,
            max_tokens=512,
        )
        try:
            response = llm_generate_fn(req)
            facts_text = response.reply_text.strip()
            if facts_text.upper() == "NONE":
                return []
            facts = [f.strip() for f in facts_text.split("\n") if f.strip()]
            memory_ids = []
            for fact in facts:
                mid = store_memory(
                    content=fact,
                    memory_type="fact",
                    source_conversation_id=conversation_id,
                )
                memory_ids.append(mid)
            return memory_ids
        except Exception as e:
            logger.warning("Failed to extract memories via LLM: %s", e)

    # Fallback: store last assistant message
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            mid = store_memory(
                content=msg["content"][:500],
                memory_type="conversation",
                source_conversation_id=conversation_id,
            )
            return [mid]
    return []
