from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # 平台超级管理员
    is_deleted = Column(Boolean, default=False)  # 软删除标记
    role = Column(String(50), default="user")

class DataSource(Base):
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    type = Column(String(50))  # postgresql, mysql
    host = Column(String(255))
    port = Column(Integer)
    username = Column(String(255))
    password_encrypted = Column(String(500))
    database_name = Column(String(255))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源
    
    datasets = relationship("Dataset", back_populates="datasource")
    owner = relationship("User")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    collection_name = Column(String(255), unique=True, index=True)
    schema_config = Column(JSON)  # e.g. ["users", "orders"]
    training_status = Column(String(50), default="pending")  # pending, training, completed, failed
    last_trained_at = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源
    
    datasource = relationship("DataSource", back_populates="datasets")
    owner = relationship("User")
    business_terms = relationship("BusinessTerm", back_populates="dataset", cascade="all, delete-orphan")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(500), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cards = relationship("DashboardCard", back_populates="dashboard", cascade="all, delete-orphan")
    owner = relationship("User")


class DashboardCard(Base):
    __tablename__ = "dashboard_cards"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"))
    title = Column(String(255))
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    sql = Column(Text)
    chart_type = Column(String(50))  # bar/line/pie/table
    layout = Column(JSON, nullable=True)  # {x, y, w, h}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dashboard = relationship("Dashboard", back_populates="cards")
    dataset = relationship("Dataset")


class BusinessTerm(Base):
    __tablename__ = "business_terms"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    term = Column(String(255), index=True)  # 术语名称，如 "高净值客户"
    definition = Column(Text)  # 定义，如 "年消费额 > 100w 的客户"
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dataset = relationship("Dataset", back_populates="business_terms")
    owner = relationship("User")


class ChatMessage(Base):
    """会话消息模型 - 用于存储用户与 AI 的对话历史"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源（实际上聊天记录一般是私有的）
    question = Column(Text)
    answer = Column(Text, nullable=True)
    sql = Column(Text, nullable=True)
    chart_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dataset = relationship("Dataset")
    user = relationship("User", foreign_keys=[user_id])
    owner = relationship("User", foreign_keys=[owner_id])
