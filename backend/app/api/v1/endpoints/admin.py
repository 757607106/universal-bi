from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import logging

from app.api.deps import get_db, get_current_superuser
from app.models.metadata import User
from app.schemas.user import UserListOut, UserStatusUpdate, UserUpdateByAdmin, UsersListResponse
from app.core.security import get_password_hash

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/users", response_model=UsersListResponse)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大100"),
    search: Optional[str] = Query(None, description="搜索关键词，支持按 email 或 full_name 搜索")
):
    """
    获取用户列表（分页，支持搜索）
    
    权限：仅超级管理员
    
    搜索逻辑：
    - 如果提供了 search 参数，则在 email 和 full_name 中进行模糊匹配
    - 默认返回所有用户（包括已删除的用户）
    """
    # 构建查询
    query = db.query(User)
    
    # 应用搜索过滤
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )
    
    # 获取总数
    total = query.count()
    
    # 应用分页
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()
    
    logger.info(f"Admin {current_user.email} 查询用户列表，page={page}, page_size={page_size}, search={search}, total={total}")
    
    return UsersListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=users
    )


@router.patch("/users/{user_id}/status", response_model=UserListOut)
def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    修改用户状态（封禁/解封）
    
    权限：仅超级管理员
    
    功能说明：
    - 设置 is_active = False 可封禁用户，封禁后用户无法登录
    - 设置 is_active = True 可解封用户
    - 不能修改自己的状态
    """
    # 查询目标用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    
    # 防止管理员修改自己的状态
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的账户状态"
        )
    
    # 更新状态
    old_status = user.is_active
    user.is_active = status_update.is_active
    db.commit()
    db.refresh(user)
    
    action = "解封" if status_update.is_active else "封禁"
    logger.warning(
        f"Admin {current_user.email} {action}用户 {user.email} (ID: {user_id})，"
        f"状态变更: {old_status} -> {status_update.is_active}"
    )
    
    return user


@router.delete("/users/{user_id}", response_model=UserListOut)
def soft_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    软删除用户
    
    权限：仅超级管理员
    
    功能说明：
    - 将用户的 is_deleted 设为 True
    - 同时将 is_active 设为 False（防止用户继续登录）
    - 不会真正删除数据库记录，便于数据恢复和审计
    - 不能删除自己
    """
    # 查询目标用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    
    # 防止管理员删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    # 检查是否已经被删除
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户 {user.email} 已经被删除"
        )
    
    # 执行软删除
    user.is_deleted = True
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    logger.warning(
        f"Admin {current_user.email} 软删除用户 {user.email} (ID: {user_id})"
    )
    
    return user


@router.patch("/users/{user_id}", response_model=UserListOut)
def update_user(
    user_id: int,
    user_update: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    修改用户信息
    
    权限：仅超级管理员
    
    功能说明：
    - 可修改用户昵称、密码、角色
    - 仅用于紧急维护（如用户忘记密码）
    - 所有字段都是可选的，只更新提供的字段
    - 不能修改自己的信息（防止误操作）
    """
    # 查询目标用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    
    # 防止管理员修改自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能通过此接口修改自己的信息，请使用个人设置"
        )
    
    # 记录修改内容
    updates = []
    
    # 更新昵称
    if user_update.full_name is not None:
        old_name = user.full_name
        user.full_name = user_update.full_name
        updates.append(f"昵称: {old_name} -> {user_update.full_name}")
    
    # 更新密码
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
        updates.append("密码已重置")
    
    # 更新角色
    if user_update.role is not None:
        old_role = user.role
        user.role = user_update.role
        updates.append(f"角色: {old_role} -> {user_update.role}")
    
    # 如果没有任何更新
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供任何需要更新的字段"
        )
    
    # 提交更改
    db.commit()
    db.refresh(user)
    
    logger.warning(
        f"Admin {current_user.email} 修改用户 {user.email} (ID: {user_id})，"
        f"更新内容: {', '.join(updates)}"
    )
    
    return user
