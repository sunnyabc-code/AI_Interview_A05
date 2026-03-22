import argparse
import os
import sys


# Ensure project root is importable when running this file directly.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AI_Interview.settings")

import django  # noqa: E402

django.setup()

from core.llm_client import LLMClient, LLMClientError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Test LLM connectivity with current project settings.")
    parser.add_argument(
        "--prompt",
        default="Please ask one concise interview question about Python lists.",
        help="User prompt sent to the model.",
    )
    parser.add_argument(
        "--system",
        default="You are a strict interviewer. Return exactly one question in plain text.",
        help="System prompt.",
    )
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, default=128, help="Max response tokens.")
    args = parser.parse_args()

    client = LLMClient.from_settings()

    print("[INFO] LLM_BASE_URL:", client.base_url)
    print("[INFO] LLM_MODEL:", client.model)
    print("[INFO] LLM_TIMEOUT_SECONDS:", client.timeout_seconds)
    print("[INFO] API key configured:", bool(client.api_key))

    if not client.is_configured():
        print("[ERROR] LLM is not configured. Please set LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL.")
        return 2

    try:
        question = client.generate_question_from_prompt(
            prompt=args.prompt,
            system_prompt=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except LLMClientError as exc:
        print("[ERROR] LLM request failed:", exc)
        return 1

    print("\n[SUCCESS] LLM reachable. Generated content:")
    print(question)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
