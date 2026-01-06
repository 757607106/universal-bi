from urllib.parse import quote_plus
from sqlalchemy import create_engine, text, MetaData, Table, select, inspect
from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date
from decimal import Decimal
from app.models.metadata import DataSource
from app.core.security import decrypt_password
import logging

logger = logging.getLogger(__name__)

class DBInspector:
    @staticmethod
    def _build_url(type_: str, user: str, password: str, host: str, port: int, db: str) -> str:
        if type_ == "sqlite":
            # For SQLite, host is treated as the file path
            return f"sqlite:///{host}"

        if type_ == "postgresql":
            driver = "postgresql+psycopg2"
        elif type_ == "mysql":
            driver = "mysql+pymysql"
        else:
            raise ValueError(f"Unsupported database type: {type_}")
        
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)
        
        return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{db}"

    @classmethod
    def test_connection(cls, ds_info: dict) -> bool:
        try:
            url = cls._build_url(
                ds_info["type"],
                ds_info["username"],
                ds_info["password"],  # Plain text from input
                ds_info["host"],
                int(ds_info["port"]),
                ds_info["database_name"]
            )
            # Short timeout for testing connection
            engine = create_engine(url, connect_args={"connect_timeout": 5})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    @classmethod
    def get_engine(cls, ds: DataSource):
        password = ""
        if ds.password_encrypted:
            try:
                password = decrypt_password(ds.password_encrypted)
            except Exception:
                pass
                
        url = cls._build_url(
            ds.type,
            ds.username or "",
            password,
            ds.host,
            ds.port or 0,
            ds.database_name or ""
        )
        return create_engine(url)

    @classmethod
    def get_table_names(cls, ds: DataSource) -> list:
        engine = cls.get_engine(ds)
        inspector = inspect(engine)
        return inspector.get_table_names()

    @classmethod
    def get_table_ddl(cls, ds: DataSource, table_name: str) -> str:
        engine = cls.get_engine(ds)
        metadata = MetaData()
        try:
            table = Table(table_name, metadata, autoload_with=engine)
            return str(CreateTable(table).compile(engine))
        except Exception as e:
            logger.error(f"Error generating DDL for {table_name}: {e}")
            raise ValueError(f"Failed to generate DDL for table {table_name}: {str(e)}")

    @classmethod
    def get_table_data(cls, ds: DataSource, table_name: str, limit: int = 100) -> dict:
        engine = cls.get_engine(ds)
        metadata = MetaData()
        
        try:
            # Reflect the table
            table = Table(table_name, metadata, autoload_with=engine)
            
            # Build query
            stmt = select(table).limit(limit)
            
            with engine.connect() as connection:
                result = connection.execute(stmt)
                keys = list(result.keys())
                columns = [{"prop": k, "label": k} for k in keys]
                
                rows = []
                for row in result:
                    row_data = {}
                    for i, value in enumerate(row):
                        key = keys[i]
                        if isinstance(value, (datetime, date)):
                            row_data[key] = value.isoformat()
                        elif isinstance(value, Decimal):
                            row_data[key] = float(value)
                        else:
                            row_data[key] = value
                    rows.append(row_data)
                    
                return {"columns": columns, "rows": rows}
        except Exception as e:
            logger.error(f"Error getting data for {table_name}: {e}")
            raise ValueError(f"Failed to fetch data for table {table_name}: {str(e)}")
