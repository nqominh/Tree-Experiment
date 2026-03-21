"""
run_experiment_minimax.py -- MiniMax adapter runner for the existing CSV pipeline.

This script reuses the core workflow from run_experiment_csv.py and only swaps
out the model-call function so you can run the same experiments with MiniMax
via the Anthropic-compatible API.

Usage (PowerShell):
  $env:ANTHROPIC_BASE_URL="https://api.minimax.io/anthropic"
  $env:ANTHROPIC_API_KEY="your_key"
  .venv\\Scripts\\python.exe run_experiment_minimax.py \
    --questions "tests/questions_clean_audit copy.jsonl" \
    --prompt-file prompts/C3_SchemaOnly.md \
    --output score/C3_schema_only_minimax.csv \
    --model MiniMax-M2.7 \
    --delay 2
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import anthropic
from anthropic import APIConnectionError, APIStatusError, APITimeoutError

import run_experiment_csv as base

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_BASE_URL = "https://api.minimax.io/anthropic"
MAX_RETRIES = 3
RETRY_WAIT = 30


def _extract_text_from_response(message: Any) -> str:
    """Extract text blocks from Anthropic-style response content."""
    parts: list[str] = []
    for block in getattr(message, "content", []):
        if getattr(block, "type", None) == "text":
            txt = getattr(block, "text", "")
            if isinstance(txt, str) and txt.strip():
                parts.append(txt)
    if parts:
        return "\n".join(parts)
    raise RuntimeError(f"Unexpected response shape: {json.dumps(message.model_dump())[:300]}")


def call_minimax(
    prompt: str,
    api_key: str,
    model: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call MiniMax Anthropic-compatible endpoint with retry behavior."""
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                response = stream.get_final_message()
            return _extract_text_from_response(response)
        except APIStatusError as e:
            status_code = getattr(e.response, "status_code", None)
            body = str(e)[:300]
            if status_code in RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {status_code}: {body}"
                print(
                    f"  [retry {attempt}/{MAX_RETRIES}] {last_error[:80]}... waiting {RETRY_WAIT}s"
                )
                time.sleep(RETRY_WAIT)
                continue
            raise RuntimeError(f"HTTP {status_code}: {body}") from e
        except (APIConnectionError, APITimeoutError) as e:
            last_error = str(e)
            print(
                f"  [retry {attempt}/{MAX_RETRIES}] {type(e).__name__}: {str(e)[:80]}... waiting {RETRY_WAIT}s"
            )
            time.sleep(RETRY_WAIT)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries. Last error: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MiniMax Table QA - CSV output")
    parser.add_argument("--questions", default=str(base.QUESTIONS_PATH))
    parser.add_argument("--output", default="score/minimax_results.csv")
    parser.add_argument("--model", default="MiniMax-M2.7")
    parser.add_argument("--limit", type=int, default=0, help="0 = all questions")
    parser.add_argument("--qid", type=str, default="", help="Comma-separated IDs")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")

    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default="ANTHROPIC_API_KEY")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ANTHROPIC_BASE_URL", DEFAULT_BASE_URL),
    )

    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=32000)

    parser.add_argument("--prompt-file", type=str, default=str(base.DEFAULT_PROMPT))
    parser.add_argument("--csv-dir", type=str, default="")
    parser.add_argument("--json-dir", type=str, default="")
    parser.add_argument("--html-dir", type=str, default="")
    parser.add_argument("--demo", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = args.api_key or os.environ.get(args.api_key_env)
    if not api_key and not args.demo:
        raise SystemExit(
            f"ERROR: Set {args.api_key_env} env var or pass --api-key"
        )

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        raise SystemExit(f"ERROR: Prompt file not found: {prompt_path}")

    # Monkey-patch the runner's model call so base.run uses MiniMax.
    base.call_gemini = lambda prompt, api_key, model, temperature=1.0, max_tokens=32000: call_minimax(
        prompt=prompt,
        api_key=api_key,
        model=model,
        base_url=args.base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    prompt_template = base.load_prompt_template(prompt_path)
    qids = [q.strip() for q in args.qid.split(",") if q.strip()] if args.qid else None

    print(f"Prompt template: {prompt_path.name}")
    print(f"Provider: MiniMax via Anthropic-compatible API  |  Base URL: {args.base_url}")

    base.run(
        questions_path=Path(args.questions),
        output_csv=Path(args.output),
        api_key=api_key or "",
        model=args.model,
        limit=args.limit,
        delay=args.delay,
        qids=qids,
        prompt_template=prompt_template,
        csv_dir=args.csv_dir,
        json_dir=args.json_dir,
        html_dir=args.html_dir,
        demo=args.demo,
    )


if __name__ == "__main__":
    main()
