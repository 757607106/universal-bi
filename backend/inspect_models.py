
from vanna.core.llm.models import LlmRequest, LlmResponse
from vanna.capabilities.agent_memory.models import TextMemorySearchResult
from vanna.capabilities.agent_memory.models import TextMemory
import inspect

print("LlmRequest init params:")
print(inspect.signature(LlmRequest.__init__))

print("\nLlmResponse init params:")
print(inspect.signature(LlmResponse.__init__))

print("\nTextMemorySearchResult fields:")
print(TextMemorySearchResult.__annotations__)

print("\nTextMemory fields:")
print(TextMemory.__annotations__)
