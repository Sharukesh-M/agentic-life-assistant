"""
Real LLM Smoke Test Script for JARVIX.
Executes live API call if environment credentials exist; otherwise reports NOT RUN cleanly.
"""

import sys
import os
import time

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.llm.config import LLMConfig
from app.llm.provider import get_llm_provider, OpenAILikeLLMProvider
from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext

def run_smoke_test():
    print("==================================================")
    print("JARVIX Real LLM Provider Smoke Test")
    print("==================================================")

    config = LLMConfig.from_env()
    print(f"Provider Configured: {config.provider}")
    print(f"Model Configured:    {config.model}")
    print(f"API Key Present:     {'YES' if config.api_key else 'NO'}")

    if config.provider == "mock" or not config.api_key:
        print("\nREAL LLM SMOKE TEST: NOT RUN — credentials/provider unavailable")
        print("To run live smoke test, configure LLM_PROVIDER and LLM_API_KEY environment variables.")
        return False

    print("\nExecuting live API call against provider...")
    provider = get_llm_provider(config)
    orchestrator = JARVIXOrchestrator(llm_provider=provider)

    context = AgentContext(user_id="smoke_test_user")
    start = time.time()
    result = orchestrator.execute_pipeline("Hello JARVIX, what can you help me with?", context)
    latency = time.time() - start

    print("\n==================================================")
    print("Smoke Test Execution Result:")
    print("==================================================")
    print(f"Status:          {result.get('status')}")
    print(f"Intent:          {result.get('intent')}")
    print(f"Provider Used:   {result.get('provider')}")
    print(f"Latency:         {latency:.2f} s")
    print(f"Response Body:   {result.get('result')}")
    return True

if __name__ == "__main__":
    run_smoke_test()
