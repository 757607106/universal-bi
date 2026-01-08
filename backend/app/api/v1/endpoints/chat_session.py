"""
会话管理API端点 - 管理聊天会话和消息历史
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.metadata import User, ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageResponse
)
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[ChatSessionResponse])
def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的会话列表
    按更新时间倒序排列
    """
    sessions = db.query(ChatSession).filter(
        ChatSession.owner_id == current_user.id
    ).order_by(
        ChatSession.updated_at.desc()
    ).offset(skip).limit(limit).all()

    return sessions


@router.post("/", response_model=ChatSessionResponse)
def create_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新会话
    """
    session = ChatSession(
        title=session_in.title or "新会话",
        dataset_id=session_in.dataset_id,
        owner_id=current_user.id
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "Chat session created",
        user_id=current_user.id,
        session_id=session.id,
        title=session.title
    )

    return session


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取会话详情（包含所有消息）
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: int,
    session_in: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新会话（标题等）
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_in.title is not None:
        session.title = session_in.title

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    logger.info(
        "Chat session updated",
        user_id=current_user.id,
        session_id=session.id,
        new_title=session.title
    )

    return session


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除会话（级联删除所有消息）
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    logger.info(
        "Chat session deleted",
        user_id=current_user.id,
        session_id=session_id
    )

    return {"message": "Session deleted successfully"}


@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取会话的消息列表
    """
    # 验证会话存在且属于当前用户
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(
        ChatMessage.created_at.asc()
    ).offset(skip).limit(limit).all()

    return messages
