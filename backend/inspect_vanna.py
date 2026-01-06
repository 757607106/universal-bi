
import inspect
from vanna.core import Agent
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.legacy.chromadb import ChromaDB_VectorStore

print("--- ChromaAgentMemory methods ---")
print([m for m in dir(ChromaAgentMemory) if not m.startswith('_')])

print("\n--- ChromaDB_VectorStore methods ---")
print([m for m in dir(ChromaDB_VectorStore) if not m.startswith('_')])

print("\n--- Agent methods ---")
print([m for m in dir(Agent) if not m.startswith('_')])
