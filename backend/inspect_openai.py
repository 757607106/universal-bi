
import inspect
from vanna.integrations.openai import OpenAILlmService
print([m for m in dir(OpenAILlmService) if not m.startswith('_')])
