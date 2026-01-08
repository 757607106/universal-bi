"""
Vanna 基础类

包含 VannaLegacy 和 VannaLegacyPGVector 类，以及相关的辅助类。
"""

import uuid
import pandas as pd
from openai import OpenAI as OpenAIClient

# Standard Vanna Imports for Mixin Pattern
from vanna.legacy.openai import OpenAI_Chat
from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.core.user import User, UserResolver, RequestContext

from app.core.logger import get_logger

# PGVector support (optional, loaded dynamically)
try:
    from vanna.legacy.pgvector import PG_VectorStore
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    PG_VectorStore = None

logger = get_logger(__name__)


# Custom Exception for Training Control
class TrainingStoppedException(Exception):
    """自定义异常：训练被用户中断"""
    pass


class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Legacy Vanna class for SQL generation
    Combines ChromaDB vector store with OpenAI chat
    使用传入的 chroma_client 避免重复创建导致的冲突
    """
    def __init__(self, config=None, chroma_client=None):
        # 保存 config 引用，供父类方法使用
        self.config = config or {}
        
        # 启用 LLM 数据可见性，支持 intermediate_sql 推理
        self.allow_llm_to_see_data = True

        # === VannaBase 需要的属性 ===
        self.run_sql_is_set = False
        self.static_documentation = ""
        self.dialect = self.config.get("dialect", "SQL")
        self.language = self.config.get("language", None)
        self.max_tokens = self.config.get("max_tokens", 14000)

        # === ChromaDB_VectorStore 需要的属性 ===
        n_results = config.get('n_results', 10) if config else 10
        self.n_results_sql = config.get('n_results_sql', n_results) if config else n_results
        self.n_results_documentation = config.get('n_results_documentation', n_results) if config else n_results
        self.n_results_ddl = config.get('n_results_ddl', n_results) if config else n_results

        # 如果传入了 chroma_client，直接使用而不调用父类的 __init__
        if chroma_client is not None:
            import chromadb.utils.embedding_functions as embedding_functions

            self.chroma_client = chroma_client
            collection_name = config.get('collection_name', 'vanna_collection') if config else 'vanna_collection'
            self.n_results = config.get('n_results', 10) if config else 10

            # 初始化 embedding function
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

            # 创建 vanna 所需的所有 collection
            self.ddl_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_ddl",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self.documentation_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_documentation",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self.sql_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_sql",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            # 回退到原始初始化方式
            ChromaDB_VectorStore.__init__(self, config=config)

        # Initialize with custom OpenAI client
        if config and 'api_base' in config:
            self.client = OpenAIClient(
                api_key=config.get('api_key'),
                base_url=config.get('api_base')
            )
            # Store model name
            self.model = config.get('model', 'gpt-3.5-turbo')
        else:
            OpenAI_Chat.__init__(self, config=config)

    def submit_prompt(self, prompt, **kwargs):
        """
        Override submit_prompt to use custom client
        """
        if hasattr(self, 'client'):
            # Extract messages if provided in prompt
            if isinstance(prompt, list):
                messages = prompt
            else:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that generates SQL queries."},
                    {"role": "user", "content": str(prompt)}
                ]

            # Ensure all messages have valid content
            validated_messages = []
            for msg in messages:
                if isinstance(msg.get('content'), str) and msg['content'].strip():
                    validated_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

            if not validated_messages:
                raise ValueError("No valid messages to send to LLM")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=validated_messages,
                **kwargs
            )
            return response.choices[0].message.content
        else:
            return super().submit_prompt(prompt, **kwargs)


class VannaLegacyPGVector(OpenAI_Chat):
    """
    Legacy Vanna class for SQL generation with PGVector backend.
    Combines PGVector store with OpenAI chat (DashScope compatible).
    """
    def __init__(self, config=None):
        # 保存 config 引用
        self.config = config or {}
        
        # 启用 LLM 数据可见性，支持 intermediate_sql 推理
        self.allow_llm_to_see_data = True

        # === VannaBase 需要的属性 ===
        self.run_sql_is_set = False
        self.static_documentation = ""
        self.dialect = self.config.get("dialect", "SQL")
        self.language = self.config.get("language", None)
        self.max_tokens = self.config.get("max_tokens", 14000)

        # === PGVector 需要的属性 ===
        n_results = config.get('n_results', 10) if config else 10
        self.n_results_sql = config.get('n_results_sql', n_results) if config else n_results
        self.n_results_documentation = config.get('n_results_documentation', n_results) if config else n_results
        self.n_results_ddl = config.get('n_results_ddl', n_results) if config else n_results
        self.n_results = n_results

        # 连接字符串
        connection_string = config.get('connection_string')
        if not connection_string:
            raise ValueError("PGVector requires 'connection_string' in config")

        self.connection_string = connection_string
        collection_name = config.get('collection_name', 'vanna')

        # 初始化 embedding function
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embedding_function = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )
        except ImportError:
            raise ImportError("langchain-huggingface is required for PGVector. Install with: pip install langchain-huggingface")

        # 初始化 PGVector collections
        from langchain_postgres.vectorstores import PGVector

        self.sql_collection = PGVector(
            embeddings=self.embedding_function,
            collection_name=f"{collection_name}_sql",
            connection=self.connection_string,
        )
        self.ddl_collection = PGVector(
            embeddings=self.embedding_function,
            collection_name=f"{collection_name}_ddl",
            connection=self.connection_string,
        )
        self.documentation_collection = PGVector(
            embeddings=self.embedding_function,
            collection_name=f"{collection_name}_documentation",
            connection=self.connection_string,
        )

        logger.info(f"Initialized VannaLegacyPGVector with collection: {collection_name}")

        # Initialize with custom OpenAI client
        if config and 'api_base' in config:
            self.client = OpenAIClient(
                api_key=config.get('api_key'),
                base_url=config.get('api_base')
            )
            self.model = config.get('model', 'gpt-3.5-turbo')
        else:
            OpenAI_Chat.__init__(self, config=config)

    def submit_prompt(self, prompt, **kwargs):
        """Override submit_prompt to use custom client"""
        if hasattr(self, 'client'):
            if isinstance(prompt, list):
                messages = prompt
            else:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that generates SQL queries."},
                    {"role": "user", "content": str(prompt)}
                ]

            validated_messages = []
            for msg in messages:
                if isinstance(msg.get('content'), str) and msg['content'].strip():
                    validated_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

            if not validated_messages:
                raise ValueError("No valid messages to send to LLM")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=validated_messages,
                **kwargs
            )
            return response.choices[0].message.content
        else:
            return super().submit_prompt(prompt, **kwargs)

    # === PGVector Storage Methods ===
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Add DDL to PGVector"""
        from langchain_core.documents import Document
        doc_id = str(uuid.uuid4())
        doc = Document(page_content=ddl, metadata={"id": doc_id})
        self.ddl_collection.add_documents([doc], ids=[doc_id])
        return doc_id

    def add_documentation(self, documentation: str, **kwargs) -> str:
        """Add documentation to PGVector"""
        from langchain_core.documents import Document
        doc_id = str(uuid.uuid4())
        doc = Document(page_content=documentation, metadata={"id": doc_id})
        self.documentation_collection.add_documents([doc], ids=[doc_id])
        return doc_id

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add question-SQL pair to PGVector"""
        from langchain_core.documents import Document
        doc_id = str(uuid.uuid4())
        content = f"Question: {question}\nSQL: {sql}"
        doc = Document(page_content=content, metadata={"id": doc_id, "question": question, "sql": sql})
        self.sql_collection.add_documents([doc], ids=[doc_id])
        return doc_id

    def get_related_ddl(self, question: str, **kwargs) -> list:
        """Get related DDL from PGVector"""
        results = self.ddl_collection.similarity_search(question, k=self.n_results_ddl)
        return [doc.page_content for doc in results]

    def get_related_documentation(self, question: str, **kwargs) -> list:
        """Get related documentation from PGVector"""
        results = self.documentation_collection.similarity_search(question, k=self.n_results_documentation)
        return [doc.page_content for doc in results]

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Get similar question-SQL pairs from PGVector"""
        results = self.sql_collection.similarity_search(question, k=self.n_results_sql)
        qa_pairs = []
        for doc in results:
            if hasattr(doc, 'metadata') and 'question' in doc.metadata and 'sql' in doc.metadata:
                qa_pairs.append({
                    "question": doc.metadata['question'],
                    "sql": doc.metadata['sql']
                })
        return qa_pairs

    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """Get all training data from PGVector"""
        data = []

        # Get DDLs
        try:
            ddl_results = self.ddl_collection.similarity_search("", k=1000)
            for doc in ddl_results:
                data.append({
                    "id": doc.metadata.get('id', ''),
                    "training_data_type": "ddl",
                    "content": doc.page_content
                })
        except Exception:
            pass

        # Get Documentation
        try:
            doc_results = self.documentation_collection.similarity_search("", k=1000)
            for doc in doc_results:
                data.append({
                    "id": doc.metadata.get('id', ''),
                    "training_data_type": "documentation",
                    "content": doc.page_content
                })
        except Exception:
            pass

        # Get SQL QA pairs
        try:
            sql_results = self.sql_collection.similarity_search("", k=1000)
            for doc in sql_results:
                data.append({
                    "id": doc.metadata.get('id', ''),
                    "training_data_type": "sql",
                    "question": doc.metadata.get('question', ''),
                    "content": doc.page_content
                })
        except Exception:
            pass

        return pd.DataFrame(data)

    def remove_training_data(self, id: str) -> bool:
        """Remove training data by ID"""
        try:
            # Try to delete from all collections
            for collection in [self.ddl_collection, self.documentation_collection, self.sql_collection]:
                try:
                    collection.delete(ids=[id])
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"Failed to remove training data {id}: {e}")
            return False

    def generate_embedding(self, data: str, **kwargs) -> list:
        """Generate embedding using HuggingFace model"""
        return self.embedding_function.embed_query(data)

    def system_message(self, message: str) -> dict:
        """Create a system message"""
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        """Create a user message"""
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        """Create an assistant message"""
        return {"role": "assistant", "content": message}


class SimpleUserResolver(UserResolver):
    """简单的用户解析器，返回默认管理员用户"""
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="admin", email="admin@example.com", group_memberships=['admin'])
