from fastapi import APIRouter, HTTPException, Query

from app.services import store

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/all")
def export_all(format: str = Query("sft"), min_quality: int | None = Query(None)):
    conversations = store.list_conversations()

    if format == "json":
        data = [store.export_conversation(conv["id"]) for conv in conversations]
        if min_quality is None:
            return data
        filtered = []
        for item in data:
            scores = [
                m.get("quality_score") for m in item["meta"] if m.get("quality_score") is not None
            ]
            if scores and max(scores) >= min_quality:
                filtered.append(item)
        return filtered

    if format == "sft":
        data = []
        for conv in conversations:
            exported = store.export_sft(conv["id"])
            if not exported:
                continue
            if min_quality is None:
                data.extend(exported)
                continue
            score = exported[0].get("metadata", {}).get("quality_score")
            if score is not None and score >= min_quality:
                data.extend(exported)
        return data

    if format == "kd":
        return store.export_kd_examples(min_quality=min_quality)

    raise HTTPException(status_code=400, detail="format must be one of: json, sft, kd")


@router.get("/{conversation_id}")
def export_conversation(conversation_id: str, format: str = Query("json")):
    conversation = store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if format == "json":
        return store.export_conversation(conversation_id)
    if format == "sft":
        return store.export_sft(conversation_id)
    if format == "kd":
        return store.export_kd_examples(conversation_id=conversation_id)
    raise HTTPException(status_code=400, detail="format must be one of: json, sft, kd")


@router.get("/all/sft")
def export_all_sft(min_quality: int | None = Query(None)):
    return export_all(format="sft", min_quality=min_quality)
