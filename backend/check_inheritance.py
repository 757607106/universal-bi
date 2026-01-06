
from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.integrations.chromadb import ChromaAgentMemory
try:
    print(f"Is ChromaDB_VectorStore subclass of ChromaAgentMemory? {issubclass(ChromaDB_VectorStore, ChromaAgentMemory)}")
except Exception as e:
    print(f"Error checking subclass: {e}")

print(f"ChromaDB_VectorStore bases: {ChromaDB_VectorStore.__bases__}")
