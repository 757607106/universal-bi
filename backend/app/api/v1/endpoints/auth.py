from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core import security
from app.core.config import settings
from app.models.metadata import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserOut, User as UserSchema
from app.api.deps import get_current_user, reusable_oauth2

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    通过账号密码登录
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # 先检查用户是否存在
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号不存在，请先注册",
        )
    
    # 再检查密码是否正确
    if not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码错误，请重新输入",
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已被禁用，请联系管理员"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserOut)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    
    参数:
    - **username**: 登录账号 (必填，3-50位)
    - **email**: 用户邮箱 (必填，需要有效邮箱格式)
    - **password**: 用户密码 (必填，至少6位)
    - **full_name**: 用户全名 (可选)
    - **company**: 公司信息 (可选)
    
    返回:
    - 创建成功的用户信息（不包含密码）
    """
    # 1. 检查 username 是否已存在
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该账号已被注册",
        )
    
    # 2. 检查 email 是否已存在
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该邮箱已被注册",
        )
    
    # 3. 对密码进行 Hash 加密
    hashed_password = security.get_password_hash(user_in.password)
    
    # 4. 创建 User 对象并存入数据库
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        company=user_in.company,
        is_active=True,  # 新用户默认激活
        role="user"  # 默认角色为普通用户
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 5. 返回创建成功的 User 对象
    return user


@router.post("/logout")
def logout(
    token: str = Depends(reusable_oauth2),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    用户退出登录，将 Token 加入黑名单
    
    功能:
    1. 获取当前用户的 Token
    2. 解析 Token 计算剩余有效期
    3. 将 Token 存入 Redis 黑名单，过期时间为剩余有效期
    4. 返回成功消息
    
    注意:
    - 如果 Redis 不可用，会返回警告但仍然成功（降级策略）
    - Token 一旦加入黑名单，就无法再次使用
    """
    # 将 Token 添加到黑名单
    success = security.add_token_to_blacklist(token)
    
    if success:
        return {
            "message": "退出成功，Token 已撤销",
            "detail": "Your session has been terminated successfully"
        }
    else:
        # Redis 不可用，但仍然返回成功（降级策略）
        return {
            "message": "退出成功（警告：Token 黑名单功能不可用）",
            "detail": "Logged out successfully, but token blacklist is unavailable",
            "warning": "Token may still be valid until expiration"
        }


@router.get("/me", response_model=UserSchema)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取当前登录用户信息
    
    返回:
    - 当前用户的详细信息（包括 is_superuser 等权限字段）
    """
    return current_user
