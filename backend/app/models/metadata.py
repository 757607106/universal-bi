from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class DataSource(Base):
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)  # postgresql, mysql
    host = Column(String)
    port = Column(Integer)
    username = Column(String)
    password_encrypted = Column(String)
    database_name = Column(String)
    
    datasets = relationship("Dataset", back_populates="datasource")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    collection_name = Column(String, unique=True, index=True)
    schema_config = Column(JSON)  # e.g. ["users", "orders"]
    training_status = Column(String, default="pending")  # pending, training, completed, failed
    last_trained_at = Column(DateTime, nullable=True)
    
    datasource = relationship("DataSource", back_populates="datasets")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cards = relationship("DashboardCard", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardCard(Base):
    __tablename__ = "dashboard_cards"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"))
    title = Column(String)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    sql = Column(Text)
    chart_type = Column(String)  # bar/line/pie/table
    layout = Column(JSON, nullable=True)  # {x, y, w, h}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dashboard = relationship("Dashboard", back_populates="cards")
    dataset = relationship("Dataset")
