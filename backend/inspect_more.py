
import inspect
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core.llm.models import LlmRequest, LlmResponse

try:
    print(f"ChromaAgentMemory.save_text_memory: {inspect.signature(ChromaAgentMemory.save_text_memory)}")
except Exception as e:
    print(f"Error: {e}")

try:
    print(f"LlmRequest fields: {LlmRequest.model_fields.keys()}")
    print(f"LlmResponse fields: {LlmResponse.model_fields.keys()}")
except Exception as e:
    print(f"Pydantic Error: {e}")
