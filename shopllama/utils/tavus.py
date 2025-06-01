import os, requests, json, logging, uuid, pathlib

TAVUS_API_KEY = os.getenv("TAVUS_API_KEY")
TAVUS_URL     = "https://api.tavus.io/v1/tts"
HEADERS       = {
    "Authorization": f"Bearer {TAVUS_API_KEY}",
    "Content-Type": "application/json"
}

def tts(text: str, voice="en-US-Neural2-F") -> pathlib.Path:
    data = {
        "input": {"text": text},
        "voice": {"name": voice},
        "audioConfig": {"audioEncoding": "MP3"}
    }
    r = requests.post(TAVUS_URL, headers=HEADERS, json=data, timeout=45)
    r.raise_for_status()
    out = pathlib.Path(f"audio_{uuid.uuid4()}.mp3")
    out.write_bytes(r.content)
    return out 