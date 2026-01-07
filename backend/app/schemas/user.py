from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="登录账号")
    email: EmailStr
    full_name: Optional[str] = None
    company: Optional[str] = Field(None, max_length=255, description="公司信息")

class UserCreate(UserBase):
    """用户注册时的输入数据模型"""
    password: str = Field(..., min_length=6, description="密码长度至少为6位")

class UserOut(BaseModel):
    """用户返回数据模型（不包含密码）"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    company: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class User(BaseModel):
    """用户完整数据模型"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    company: Optional[str] = None
    is_active: bool
    is_superuser: bool
    role: str

    class Config:
        from_attributes = True


# ============= 管理员接口相关 Schema =============

class UserListOut(BaseModel):
    """管理员获取用户列表返回的用户模型"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    company: Optional[str] = None
    is_active: bool
    is_superuser: bool
    is_deleted: bool
    role: str

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    """更新用户状态（封禁/解封）"""
    is_active: bool = Field(..., description="用户激活状态，False表示封禁")


class UserUpdateByAdmin(BaseModel):
    """管理员修改用户信息"""
    full_name: Optional[str] = Field(None, description="用户昵称")
    password: Optional[str] = Field(None, min_length=6, description="新密码，长度至少为6位")
    role: Optional[str] = Field(None, description="用户角色")


class UsersListResponse(BaseModel):
    """用户列表响应"""
    total: int = Field(..., description="总用户数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    users: list[UserListOut] = Field(..., description="用户列表")
