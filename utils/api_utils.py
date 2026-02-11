"""
api_utils.py — LLM API Utilities

Provides llm_generate() for making LLM requests via the OpenAI-compatible API.
"""

import traceback
import time

from openai import OpenAI

from utils.constants import *


def llm_generate(
    prompt,
    key=LLM_API_KEY,
    url=LLM_API_URL,
    model=LLM_MODEL_TYPE,
    max_tokens=8192,
    temperature=0.5
):
    """Send a prompt to the LLM and return the response text."""
    client = OpenAI(api_key=key, base_url=url)

    res = "None"
    cnt = 0
    while cnt < 20:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant skilled in handling tabular data."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            res = response.choices[0].message.content
            break
        except Exception as e:
            print(f"LLM API Request Failed! Retry {cnt}!")
            traceback.print_exc()
            time.sleep(0.1)
            cnt += 1

    return res
