from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)  # 登录账号
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    company = Column(String(255), nullable=True)  # 公司信息
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
    datasource_id = Column(Integer, ForeignKey("datasources.id"), nullable=True)  # 对于 DuckDB 数据集，可为 NULL
    collection_name = Column(String(255), unique=True, index=True)
    schema_config = Column(JSON)  # e.g. ["users", "orders"]
    status = Column(String(50), default="pending")  # pending, training, completed, failed, paused
    modeling_config = Column(JSON, nullable=True, comment="存储前端可视化建模的画布数据(nodes/edges)")
    process_rate = Column(Integer, default=0, comment="训练进度百分比 0-100")
    error_msg = Column(Text, nullable=True)
    last_train_at = Column(DateTime, nullable=True)
    duckdb_path = Column(String(500), nullable=True, comment="DuckDB 数据库文件路径，用于多表分析")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源
    
    datasource = relationship("DataSource", back_populates="datasets")
    owner = relationship("User")
    business_terms = relationship("BusinessTerm", back_populates="dataset", cascade="all, delete-orphan")
    training_logs = relationship("TrainingLog", back_populates="dataset", cascade="all, delete-orphan")


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


class TrainingLog(Base):
    """训练日志模型 - 记录数据集训练过程的日志"""
    __tablename__ = "training_logs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    content = Column(Text)  # 日志内容
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dataset = relationship("Dataset", back_populates="training_logs")


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


class ChatSession(Base):
    """会话模型 - 用于分组管理用户的聊天会话"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="新会话")  # 会话标题，默认取首条消息前20字符
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)  # 关联的数据集（可选）
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 会话所有者
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("Dataset")
    owner = relationship("User")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """会话消息模型 - 用于存储用户与 AI 的对话历史"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)  # 关联会话
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 为 None 则为公共资源（实际上聊天记录一般是私有的）
    role = Column(String(20), default="user")  # user/assistant
    question = Column(Text)
    answer = Column(Text, nullable=True)
    sql = Column(Text, nullable=True)
    chart_type = Column(String(50), nullable=True)
    chart_data = Column(JSON, nullable=True)  # 存储图表数据
    insight = Column(Text, nullable=True)  # AI分析洞察
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
    dataset = relationship("Dataset")
    user = relationship("User", foreign_keys=[user_id])
    owner = relationship("User", foreign_keys=[owner_id])


class ComputedMetric(Base):
    """计算指标模型 - 存储业务指标定义、计算公式和语义描述"""
    __tablename__ = "computed_metrics"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    name = Column(String(255), index=True, nullable=False)  # 指标名称，如"客单价"
    formula = Column(Text, nullable=False)  # SQL表达式，如 "SUM(gmv) / COUNT(DISTINCT user_id)"
    description = Column(Text, nullable=True)  # 业务口径描述
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("Dataset")
    owner = relationship("User")


class DashboardTemplate(Base):
    """看板模板模型 - 用于保存和分享看板配置"""
    __tablename__ = "dashboard_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(String(500), nullable=True)
    source_dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=True)  # 来源看板（可选）
    config = Column(JSON, nullable=False)  # 存储卡片配置的快照
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)  # 是否公开（支持公开模板）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_dashboard = relationship("Dashboard")
    owner = relationship("User")
