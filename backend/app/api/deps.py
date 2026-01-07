from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.config import settings
from app.core.security import is_token_blacklisted
from app.db.session import get_db
from app.models.metadata import User
from app.schemas.token import TokenData

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    """
    获取当前用户，并进行安全检查
    
    安全检查项：
    1. Token 是否在黑名单中（已退出）
    2. Token 签名是否有效
    3. 用户是否被软删除 (is_deleted)
    4. 用户是否被封禁 (is_active)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # === 安全检查 1: Token 黑名单 ===
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # === 安全检查 2: Token 签名验证 ===
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # === 安全检查 3 & 4: 用户状态检查 ===
    user = db.query(User).filter(
        User.username == token_data.username
    ).first()
    
    if user is None:
        raise credentials_exception
    
    # 检查用户是否已被软删除
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否被封禁
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    检查当前用户是否为超级管理员
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )
    return current_user


def apply_ownership_filter(query, model, current_user: User):
    """
    应用数据隔离过滤逻辑
    
    逻辑：
    - 普通用户：只能查看 owner_id == current_user.id 或 owner_id IS NULL 的数据
    - 超级管理员：可以查看所有数据
    
    Args:
        query: SQLAlchemy Query 对象
        model: 模型类（必须有 owner_id 字段）
        current_user: 当前用户
    
    Returns:
        过滤后的 Query 对象
    """
    if current_user.is_superuser:
        # 超级管理员可以查看所有数据
        return query
    
    # 普通用户：只能查看自己的数据或公共资源
    return query.filter(
        or_(
            model.owner_id == current_user.id,
            model.owner_id.is_(None)
        )
    )
