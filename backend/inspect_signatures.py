
import inspect
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core import Agent

try:
    print(f"OpenAILlmService.send_request: {inspect.signature(OpenAILlmService.send_request)}")
except Exception as e:
    print(f"OpenAILlmService.send_request error: {e}")

try:
    print(f"ChromaAgentMemory.search_text_memories: {inspect.signature(ChromaAgentMemory.search_text_memories)}")
except Exception as e:
    print(f"ChromaAgentMemory.search_text_memories error: {e}")

try:
    print(f"Agent.train exists? {'train' in dir(Agent)}")
except Exception as e:
    print(f"Agent check error: {e}")
