
import sys
import os
from sqlalchemy import create_engine, inspect

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.metadata import Dataset
from app.services.db_inspector import DBInspector

def inspect_dataset_tables(dataset_id=7):
    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            print(f"Dataset {dataset_id} not found")
            return

        print(f"Dataset: {dataset.name}, Datasource: {dataset.datasource.name}")
        
        # Get engine
        engine = DBInspector.get_engine(dataset.datasource)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables in DB: {tables}")
        
    finally:
        db.close()

if __name__ == "__main__":
    inspect_dataset_tables()
