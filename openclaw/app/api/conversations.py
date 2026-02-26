from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    ConversationResponse,
    CreateConversationRequest,
    UpdateConversationRequest,
)
from app.services import store

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(req: CreateConversationRequest = CreateConversationRequest()):
    return store.create_conversation(req.title)


@router.get("")
def list_conversations():
    return store.list_conversations()


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str):
    conversation = store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def patch_conversation(conversation_id: str, req: UpdateConversationRequest):
    conversation = store.update_conversation(conversation_id, req.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str):
    deleted = store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str):
    if not store.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return store.get_messages(conversation_id)
