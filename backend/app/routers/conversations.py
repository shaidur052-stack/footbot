"""Conversation history. All routes require auth — history is per-user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import chat_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return chat_service.list_conversations(db, user.id)


@router.get("/{conv_id}")
def get_one(conv_id: int, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    conv = chat_service.get_conversation(db, user.id, conv_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.delete("/{conv_id}", status_code=204)
def remove(conv_id: int, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    if not chat_service.delete_conversation(db, user.id, conv_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")