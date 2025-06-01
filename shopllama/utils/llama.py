import os, requests, json, logging

LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
LLAMA_URL     = os.getenv("LLAMA_URL", "https://api.meta.ai/v1/chat/completions")

HEADERS = {
    "Authorization": f"Bearer {LLAMA_API_KEY}",
    "Content-Type": "application/json"
}

def chat_llama(messages: list, tools: list | None = None, stream=False):
    """
    Wrapper around Meta Llama 4 chat-completion (OpenAI-style).
    `messages` is a standard list of {role, content}.
    """
    payload = {
        "model": "meta_llama/Llama-4-Scout-17B-16E-Instruct",  # or Maverick for vision
        "messages": messages,
        "stream": stream,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        r = requests.post(LLAMA_URL, headers=HEADERS, json=payload, timeout=45)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logging.exception("Llama API error")
        raise RuntimeError(e) 