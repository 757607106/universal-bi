
import inspect
from vanna.integrations.openai import OpenAILlmService
print(f"Is send_request async? {inspect.iscoroutinefunction(OpenAILlmService.send_request)}")
