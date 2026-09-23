"""
Local LLM client for MARK XL.

Supported backends:

    "ollama"
        Uses Ollama's native /api/chat endpoint.
        Default: http://127.0.0.1:11434

    "openai"
        Uses an OpenAI-compatible server such as:
        LM Studio, Jan, LocalAI, llama.cpp, vLLM, etc.

Configuration:
    config/api_keys.json

Example:
{
    "llm_provider": "ollama",
    "llm_url": "http://127.0.0.1:11434",
    "llm_model": "qwen3:0.6b"
}
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Generator

import requests


# ---------------------------------------------------------------------------
# Sentence detection
# ---------------------------------------------------------------------------

_SENT_END = re.compile(
    r"(?<=[.!?])\s+|(?<=\n)\s*\n"
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()

CONFIG_PATH = (
    BASE_DIR
    / "config"
    / "api_keys.json"
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "llm_url": "http://127.0.0.1:11434",
    "llm_model": "qwen3:0.6b",
    "llm_provider": "ollama",
}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    try:
        data = json.loads(
            CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def get_llm_provider() -> str:
    """
    Return either:

        ollama
        openai

    Aliases such as lmstudio/localai/jan are treated
    as OpenAI-compatible providers.
    """

    raw = (
        _load_config()
        .get(
            "llm_provider",
            _DEFAULTS["llm_provider"],
        )
    )

    raw = str(raw).strip().lower()

    if raw in {
        "openai",
        "lmstudio",
        "localai",
        "jan",
        "llamacpp",
        "llama.cpp",
        "vllm",
    }:
        return "openai"

    return "ollama"


def get_llm_settings() -> tuple[str, str]:
    """
    Returns:

        (base_url, model_name)
    """

    cfg = _load_config()

    url = str(
        cfg.get(
            "llm_url",
            _DEFAULTS["llm_url"],
        )
    ).rstrip("/")

    model = str(
        cfg.get(
            "llm_model",
            _DEFAULTS["llm_model"],
        )
    ).strip()

    return url, model


# ---------------------------------------------------------------------------
# Ollama health
# ---------------------------------------------------------------------------

def ensure_ollama_running(
    timeout: int = 15,
) -> bool:
    """
    Make sure the configured LLM server is reachable.

    Ollama:
        Automatically starts `ollama serve` if necessary.

    OpenAI-compatible:
        Only checks /v1/models.
    """

    url, _ = get_llm_settings()
    provider = get_llm_provider()

    # -----------------------------------------------------------------------
    # OpenAI-compatible server
    # -----------------------------------------------------------------------

    if provider == "openai":

        health_url = f"{url}/v1/models"

        try:
            response = requests.get(
                health_url,
                timeout=5,
            )

            if response.status_code == 200:
                print(
                    f"[LLM] OpenAI-compatible server "
                    f"reachable at {url}"
                )
                return True

            print(
                f"[LLM] Server at {url} returned "
                f"HTTP {response.status_code}."
            )

            return False

        except Exception:
            print(
                f"[LLM] Cannot reach OpenAI-compatible "
                f"server at {url}."
            )

            return False

    # -----------------------------------------------------------------------
    # Ollama
    # -----------------------------------------------------------------------

    health_url = f"{url}/api/tags"

    def _is_up() -> bool:
        try:
            return (
                requests.get(
                    health_url,
                    timeout=3,
                ).status_code
                == 200
            )

        except Exception:
            return False

    if _is_up():
        return True

    print(
        "[LLM] Ollama not running — "
        "launching 'ollama serve'..."
    )

    try:

        kwargs: dict = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW
            )

        subprocess.Popen(
            ["ollama", "serve"],
            **kwargs,
        )

    except FileNotFoundError:

        print(
            "[LLM] 'ollama' command not found."
        )

        return False

    except Exception as exc:

        print(
            f"[LLM] Could not launch Ollama: {exc}"
        )

        return False

    deadline = time.time() + timeout

    while time.time() < deadline:

        time.sleep(1)

        if _is_up():

            print(
                "[LLM] Ollama started successfully."
            )

            return True

    print(
        "[LLM] Ollama did not respond "
        "within the timeout."
    )

    return False


# ---------------------------------------------------------------------------
# Model availability
# ---------------------------------------------------------------------------

def check_model_available(
    log: Callable | None = None,
) -> bool:
    """
    Check whether the configured Ollama model exists locally.
    """

    if get_llm_provider() != "ollama":
        return True

    url, model = get_llm_settings()

    try:

        response = requests.get(
            f"{url}/api/tags",
            timeout=5,
        )

        response.raise_for_status()

        pulled = [
            str(item.get("name", ""))
            for item in response.json().get(
                "models",
                [],
            )
        ]

        model_base = model.split(":")[0]

        found = any(
            name == model
            or name == model_base
            or name.startswith(
                model_base + ":"
            )
            for name in pulled
        )

        if not found:

            available = (
                ", ".join(pulled)
                if pulled
                else "none"
            )

            warning = (
                f"WRN: Model '{model}' "
                f"is not pulled in Ollama.\n"
                f"     Available: {available}\n"
                f"     Fix: ollama pull {model}"
            )

            print(warning)

            if log:
                log(
                    f"WRN: '{model}' not found — "
                    f"run: ollama pull {model}"
                )

        return found

    except Exception:
        # Ollama may still be starting.
        return True


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------

def warmup_model(
    system_prompt: str | None = None,
) -> bool:
    """
    Pre-load the configured model.

    For Ollama, keep_alive=-1 keeps the model loaded.
    """

    url, model = get_llm_settings()
    provider = get_llm_provider()

    print(
        f"[LLM] Warming up '{model}' "
        f"({provider})..."
    )

    messages: list[dict] = []

    if system_prompt:
        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": "hi",
        }
    )

    # -----------------------------------------------------------------------
    # OpenAI-compatible
    # -----------------------------------------------------------------------

    if provider == "openai":

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": 1,
        }

        try:

            response = requests.post(
                f"{url}/v1/chat/completions",
                json=payload,
                timeout=180,
            )

            response.raise_for_status()

            print(
                f"[LLM] '{model}' ready."
            )

            return True

        except Exception as exc:

            print(
                f"[LLM] Warmup failed "
                f"(non-fatal): {exc}"
            )

            return False

    # -----------------------------------------------------------------------
    # Ollama
    # -----------------------------------------------------------------------

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": -1,
        "options": {
            "num_predict": 1,
            "num_gpu": 99,
        },
    }

    try:

        response = requests.post(
            f"{url}/api/chat",
            json=payload,
            timeout=180,
        )

        response.raise_for_status()

        print(
            f"[LLM] '{model}' loaded."
        )

        return True

    except Exception as exc:

        print(
            f"[LLM] Warmup failed "
            f"(non-fatal): {exc}"
        )

        return False


# ---------------------------------------------------------------------------
# Normal chat
# ---------------------------------------------------------------------------

def call_llm(
    messages: list,
    tools: list | None = None,
    timeout: int = 120,
) -> dict:
    """
    Non-streaming chat request.

    Returns:

        {
            "content": str,
            "tool_calls": list
        }
    """

    url, model = get_llm_settings()
    provider = get_llm_provider()

    # -----------------------------------------------------------------------
    # OpenAI-compatible
    # -----------------------------------------------------------------------

    if provider == "openai":

        endpoint = (
            f"{url}/v1/chat/completions"
        )

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": 150,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:

            response = requests.post(
                endpoint,
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()

            choice = (
                response.json()
                .get("choices", [{}])[0]
            )

            message = choice.get(
                "message",
                {},
            )

            raw_tool_calls = (
                message.get("tool_calls")
                or []
            )

            tool_calls = []

            for tool_call in raw_tool_calls:

                function = (
                    tool_call.get(
                        "function",
                        {},
                    )
                )

                arguments = (
                    function.get(
                        "arguments",
                        {},
                    )
                )

                if isinstance(
                    arguments,
                    str,
                ):
                    try:
                        arguments = json.loads(
                            arguments
                        )
                    except Exception:
                        arguments = {}

                tool_calls.append(
                    {
                        "id": tool_call.get(
                            "id",
                            "",
                        ),
                        "function": {
                            "name": function.get(
                                "name",
                                "",
                            ),
                            "arguments": arguments,
                        },
                    }
                )

            return {
                "content": (
                    message.get(
                        "content",
                        "",
                    )
                    or ""
                ).strip(),

                "tool_calls": tool_calls,
            }

        except Exception as exc:

            raise RuntimeError(
                "OpenAI-compatible LLM "
                f"call failed: {exc}"
            ) from exc

    # -----------------------------------------------------------------------
    # Ollama
    # -----------------------------------------------------------------------

    endpoint = f"{url}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": -1,
        "options": {
            "num_predict": 150,
            "num_gpu": 99,
        },
    }

    if tools:
        payload["tools"] = tools

    try:

        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
        )

        response.raise_for_status()

        data = response.json()

        message = data.get(
            "message",
            {},
        )

        return {
            "content": (
                message.get(
                    "content",
                    "",
                )
                or ""
            ).strip(),

            "tool_calls": (
                message.get(
                    "tool_calls"
                )
                or []
            ),
        }

    except requests.exceptions.ConnectionError as exc:

        print(
            "[LLM] ConnectionError — "
            "trying to restart Ollama..."
        )

        if ensure_ollama_running():

            try:

                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=timeout,
                )

                response.raise_for_status()

                data = response.json()

                message = data.get(
                    "message",
                    {},
                )

                return {
                    "content": (
                        message.get(
                            "content",
                            "",
                        )
                        or ""
                    ).strip(),

                    "tool_calls": (
                        message.get(
                            "tool_calls"
                        )
                        or []
                    ),
                }

            except Exception:
                pass

        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed."
        ) from exc

    except requests.exceptions.Timeout as exc:

        raise RuntimeError(
            f"Ollama request timed out "
            f"after {timeout} seconds."
        ) from exc

    except requests.exceptions.HTTPError as exc:

        status = (
            exc.response.status_code
            if exc.response
            else "unknown"
        )

        print(
            f"[LLM] HTTPError: {status}"
        )

        raise RuntimeError(
            f"Ollama HTTP error: {status}"
        ) from exc

    except Exception as exc:

        print(
            f"[LLM] Unexpected error: "
            f"{type(exc).__name__}: {exc}"
        )

        raise RuntimeError(
            f"LLM call failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Simple text generation
# ---------------------------------------------------------------------------

def call_llm_text(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    timeout: int = 120,
) -> str:
    """
    Simple text-only generation.

    Respects the configured provider.

    Used by:
        planner
        executor
        error_handler
        code_helper
        dev_agent
        memory extraction
        profile extraction
    """

    url, default_model = get_llm_settings()
    provider = get_llm_provider()

    selected_model = model or default_model

    messages: list[dict] = []

    if system:
        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    # -----------------------------------------------------------------------
    # OpenAI-compatible
    # -----------------------------------------------------------------------

    if provider == "openai":

        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "max_tokens": 600,
        }

        try:

            response = requests.post(
                f"{url}/v1/chat/completions",
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()

            return (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                or ""
            ).strip()

        except Exception as exc:

            raise RuntimeError(
                f"OpenAI-compatible "
                f"text call failed: {exc}"
            ) from exc

    # -----------------------------------------------------------------------
    # Ollama
    # -----------------------------------------------------------------------

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
        "keep_alive": -1,
        "options": {
            "num_predict": 600,
            "num_gpu": 99,
        },
    }

    endpoint = f"{url}/api/chat"

    try:

        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
        )

        response.raise_for_status()

        return (
            response.json()
            .get("message", {})
            .get("content", "")
            or ""
        ).strip()

    except requests.exceptions.ConnectionError:

        if ensure_ollama_running():

            try:

                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=timeout,
                )

                response.raise_for_status()

                return (
                    response.json()
                    .get("message", {})
                    .get("content", "")
                    or ""
                ).strip()

            except Exception:
                pass

        raise RuntimeError(
            f"Cannot connect to Ollama at {url}."
        )

    except Exception as exc:

        raise RuntimeError(
            f"LLM text call failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# OpenAI-compatible streaming
# ---------------------------------------------------------------------------

def _stream_openai(
    messages: list,
    tools: list | None,
    timeout: int,
) -> Generator[dict, None, None]:

    url, model = get_llm_settings()

    endpoint = (
        f"{url}/v1/chat/completions"
    )

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": 150,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:

        with requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            stream=True,
        ) as response:

            response.raise_for_status()

            full_content = ""
            buffer = ""

            tool_fragments: dict[
                int,
                dict
            ] = {}

            for raw in response.iter_lines():

                if not raw:
                    continue

                line = (
                    raw.decode(
                        "utf-8",
                        errors="replace",
                    )
                    if isinstance(raw, bytes)
                    else raw
                )

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)

                except json.JSONDecodeError:
                    continue

                choice = (
                    chunk.get(
                        "choices",
                        [{}],
                    )[0]
                )

                delta = choice.get(
                    "delta",
                    {},
                )

                text = (
                    delta.get(
                        "content"
                    )
                    or ""
                )

                full_content += text
                buffer += text

                # -----------------------------------------------------------
                # Sentence streaming
                # -----------------------------------------------------------

                while True:

                    match = _SENT_END.search(
                        buffer
                    )

                    if not match:
                        break

                    sentence = (
                        buffer[
                            : match.start() + 1
                        ].strip()
                    )

                    buffer = buffer[
                        match.end():
                    ]

                    if sentence:

                        yield {
                            "type": "sentence",
                            "text": sentence,
                        }

                # -----------------------------------------------------------
                # Tool calls
                # -----------------------------------------------------------

                for tool_call in (
                    delta.get("tool_calls")
                    or []
                ):

                    index = tool_call.get(
                        "index",
                        0,
                    )

                    if index not in tool_fragments:

                        tool_fragments[index] = {
                            "id": "",
                            "function": {
                                "name": "",
                                "arguments": "",
                            },
                        }

                    fragment = (
                        tool_fragments[index]
                    )

                    fragment["id"] = (
                        fragment["id"]
                        or tool_call.get(
                            "id",
                            "",
                        )
                    )

                    function = tool_call.get(
                        "function",
                        {},
                    )

                    fragment["function"][
                        "name"
                    ] += (
                        function.get(
                            "name"
                        )
                        or ""
                    )

                    fragment["function"][
                        "arguments"
                    ] += (
                        function.get(
                            "arguments"
                        )
                        or ""
                    )

                finish_reason = choice.get(
                    "finish_reason"
                )

                if finish_reason in {
                    "stop",
                    "tool_calls",
                    "length",
                }:
                    break

            # ---------------------------------------------------------------
            # Flush remaining text
            # ---------------------------------------------------------------

            if buffer.strip():

                yield {
                    "type": "sentence",
                    "text": buffer.strip(),
                }

            # ---------------------------------------------------------------
            # Final tool calls
            # ---------------------------------------------------------------

            tool_calls = []

            for index in sorted(
                tool_fragments
            ):

                fragment = (
                    tool_fragments[index]
                )

                arguments = (
                    fragment["function"][
                        "arguments"
                    ]
                )

                try:
                    arguments = json.loads(
                        arguments
                    )

                except Exception:
                    arguments = {}

                tool_calls.append(
                    {
                        "id": fragment["id"],
                        "function": {
                            "name": fragment[
                                "function"
                            ]["name"],
                            "arguments": arguments,
                        },
                    }
                )

            yield {
                "type": "done",
                "content": full_content.strip(),
                "tool_calls": tool_calls,
            }

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            f"Cannot reach OpenAI-compatible "
            f"server at {url}."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "OpenAI-compatible stream "
            "timed out."
        )

    except requests.exceptions.HTTPError as exc:

        status = (
            exc.response.status_code
            if exc.response
            else "unknown"
        )

        raise RuntimeError(
            f"OpenAI-compatible HTTP "
            f"error: {status}"
        )

    except Exception as exc:

        raise RuntimeError(
            f"OpenAI-compatible stream "
            f"failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Main streaming interface
# ---------------------------------------------------------------------------

def call_llm_stream(
    messages: list,
    tools: list | None = None,
    timeout: int = 120,
) -> Generator[dict, None, None]:
    """
    Streaming chat request.

    Yields:

        {
            "type": "sentence",
            "text": "..."
        }

    and finally:

        {
            "type": "done",
            "content": "...",
            "tool_calls": [...]
        }
    """

    provider = get_llm_provider()

    # -----------------------------------------------------------------------
    # OpenAI-compatible
    # -----------------------------------------------------------------------

    if provider == "openai":

        yield from _stream_openai(
            messages,
            tools,
            timeout,
        )

        return

    # -----------------------------------------------------------------------
    # Ollama
    # -----------------------------------------------------------------------

    url, model = get_llm_settings()

    endpoint = f"{url}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": -1,
        "options": {
            "num_predict": 150,
            "num_gpu": 99,
        },
    }

    if tools:
        payload["tools"] = tools

    def _do_stream():

        with requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            stream=True,
        ) as response:

            response.raise_for_status()

            full_content = ""
            tool_calls: list = []
            buffer = ""

            for raw in response.iter_lines():

                if not raw:
                    continue

                try:

                    chunk = json.loads(
                        raw
                    )

                except json.JSONDecodeError:
                    continue

                message = chunk.get(
                    "message",
                    {},
                )

                delta = (
                    message.get(
                        "content"
                    )
                    or ""
                )

                full_content += delta
                buffer += delta

                # -----------------------------------------------------------
                # Sentence streaming
                # -----------------------------------------------------------

                while True:

                    match = _SENT_END.search(
                        buffer
                    )

                    if not match:
                        break

                    sentence = (
                        buffer[
                            : match.start() + 1
                        ].strip()
                    )

                    buffer = buffer[
                        match.end():
                    ]

                    if sentence:

                        yield {
                            "type": "sentence",
                            "text": sentence,
                        }

                # -----------------------------------------------------------
                # Tool calls
                # -----------------------------------------------------------

                tc = message.get(
                    "tool_calls"
                )

                if tc:
                    tool_calls.extend(tc)

                # -----------------------------------------------------------
                # Finished
                # -----------------------------------------------------------

                if chunk.get("done"):

                    if buffer.strip():

                        yield {
                            "type": "sentence",
                            "text": buffer.strip(),
                        }

                    yield {
                        "type": "done",
                        "content": (
                            full_content.strip()
                        ),
                        "tool_calls": tool_calls,
                    }

                    return

    try:

        yield from _do_stream()

    except requests.exceptions.ConnectionError as exc:

        print(
            "[LLM] Stream ConnectionError — "
            "trying to restart Ollama..."
        )

        if ensure_ollama_running():

            yield from _do_stream()

            return

        raise RuntimeError(
            f"Cannot connect to Ollama at {url}."
        ) from exc

    except requests.exceptions.Timeout as exc:

        raise RuntimeError(
            "Ollama stream timed out."
        ) from exc

    except requests.exceptions.HTTPError as exc:

        status = (
            exc.response.status_code
            if exc.response
            else "unknown"
        )

        raise RuntimeError(
            f"Ollama HTTP error: {status}"
        ) from exc

    except Exception as exc:

        print(
            f"[LLM] Stream error: "
            f"{type(exc).__name__}: {exc}"
        )

        raise RuntimeError(
            f"LLM stream failed: {exc}"
        ) from exc