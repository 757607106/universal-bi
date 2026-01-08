"""
导入所有模型，确保SQLAlchemy能够识别它们
"""
from app.models.base import Base
from app.models.metadata import (
    User,
    DataSource,
    Dataset,
    Dashboard,
    DashboardCard,
    BusinessTerm,
    TrainingLog,
    ChatSession,
    ChatMessage,
    ComputedMetric,
    DashboardTemplate
)
from app.models.data_table import (
    Folder,
    DataTable,
    TableField
)

__all__ = [
    "Base",
    "User",
    "DataSource",
    "Dataset",
    "Dashboard",
    "DashboardCard",
    "BusinessTerm",
    "TrainingLog",
    "ChatSession",
    "ChatMessage",
    "ComputedMetric",
    "DashboardTemplate",
    "Folder",
    "DataTable",
    "TableField"
]
