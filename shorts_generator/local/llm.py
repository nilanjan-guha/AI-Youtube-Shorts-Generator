"""Local LLM backend — OpenAI or Gemini, selected by LLM_PROVIDER."""
from ..config import (
    GEMINI_MODEL,
    LLM_PROVIDER,
    OPENAI_MODEL,
    require_gemini_key,
    require_openai_key,
)


def call_openai_llm(prompt: str) -> str:
    """OpenAI Chat Completions backend used by --mode local."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "openai is required for --mode local. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    client = OpenAI(api_key=require_openai_key())
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def call_gemini_llm(prompt: str) -> str:
    """Gemini backend used by --mode local with automatic retry and model fallback."""
    import time
    try:
        from google import genai  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "google-genai is required for LLM_PROVIDER=gemini. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    client = genai.Client(api_key=require_gemini_key())
    
    # Priority candidates: prefer high-availability lite models first to prevent 503 / 429 quota exhaustion,
    # then fallback across multiple active Gemini versions.
    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        GEMINI_MODEL,
    ]
    models_to_try = list(dict.fromkeys([m for m in candidate_models if m]))
    
    last_err = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                print(f"[llm/gemini] requesting {model_name} (attempt {attempt + 1})...", flush=True)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                        "max_output_tokens": 8192,
                    },
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                err_str = str(e)
                last_err = e
                print(f"[llm/gemini] {model_name} attempt {attempt + 1} issue: {err_str[:80]}...", flush=True)
                # If 503 high demand or 429 rate limit, wait and try next model or retry
                if "503" in err_str or "429" in err_str:
                    time.sleep(2)
                else:
                    break

    # If all direct Gemini API calls exhaust quota, fallback dynamically to MuAPI
    try:
        from ..highlights import call_muapi_llm
        print("[llm/gemini] All Gemini quotas exhausted. Falling back to MuAPI engine...", flush=True)
        return call_muapi_llm(prompt)
    except Exception as mu_err:
        raise RuntimeError(f"All Gemini models and MuAPI fallback failed. Gemini error: {last_err} | MuAPI error: {mu_err}")


def call_local_llm(prompt: str) -> str:
    """Dispatch to the configured local LLM provider."""
    provider = (LLM_PROVIDER or "openai").strip().lower()
    if provider == "openai":
        return call_openai_llm(prompt)
    if provider == "gemini":
        return call_gemini_llm(prompt)
    raise RuntimeError(
        f"Unknown LLM_PROVIDER={provider!r}. Use 'openai' or 'gemini'."
    )
