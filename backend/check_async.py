
import inspect
from vanna.integrations.chromadb import ChromaAgentMemory

print(f"Is search_text_memories async? {inspect.iscoroutinefunction(ChromaAgentMemory.search_text_memories)}")
print(f"Is save_text_memory async? {inspect.iscoroutinefunction(ChromaAgentMemory.save_text_memory)}")
