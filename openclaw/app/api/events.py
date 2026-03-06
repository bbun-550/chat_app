import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services import store
from app.services.store import now_iso

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_events(unread_only: bool = False, limit: int = 50):
    return store.list_events(unread_only=unread_only, limit=limit)


@router.post("/{event_id}/read")
def mark_read(event_id: str):
    store.mark_event_read(event_id)
    return {"event_id": event_id, "is_read": 1}


@router.get("/stream")
async def event_stream(last_event_time: str = Query(default="")):
    """SSE endpoint for real-time event delivery to the iOS/macOS app.

    Client connects and receives events as they are created.
    Uses polling with a 2-second interval.
    """
    async def generate():
        cursor = last_event_time or now_iso()
        while True:
            events = store.get_events_after(cursor)
            for event in events:
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
                cursor = event["created_at"]
            await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
