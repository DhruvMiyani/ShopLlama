import os
import requests
import json
import speech_recognition as sr
import uuid
import time

# API Keys
LLAMA_API_KEY = 'LLM|1245705104001779|zbn6HjpcOleaP0XHLL-vKw_n2Bw'
TAVUS_API_KEY = '12032643152644c19e18bc16969287c3'

# API endpoints
LLAMA_URL = "https://api.llama.com/v1/chat/completions"
TAVUS_TTS_URL = "https://tavusapi.com/v2/tts"
TAVUS_LIPSYNC_URL = "https://tavusapi.com/v2/lipsync"

# Default video for lipsync
DEFAULT_VIDEO_URL = "https://cdn.replica.tavus.io/sample-videos/20283/replica-talking-head.mp4"

# Headers
llama_headers = {
    "Authorization": f"Bearer {LLAMA_API_KEY}",
    "Content-Type": "application/json"
}

tavus_headers = {
    "x-api-key": TAVUS_API_KEY,
    "Content-Type": "application/json"
}

def get_speech_input():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("🎤 Speak now... (you have ~10 seconds)")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)

    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("❌ Sorry, I could not understand that.")
        return None
    except sr.RequestError as e:
        print(f"❌ API error: {e}")
        return None

def call_llama_api(prompt):
    payload = {
        "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Generate concise, clear content suitable for voice narration."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    try:
        response = requests.post(LLAMA_URL, headers=llama_headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['completion_message']['content']['text']
    except Exception as e:
        print(f"Error calling Llama API: {e}")
        return None

def call_tavus_tts(text):
    tavus_data = {
        "input": {"text": text},
        "voice": {"name": "en-US-Neural2-F"},
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 1.0,
            "pitch": 0.0
        }
    }

    try:
        response = requests.post("https://tavusapi.com/v2/tts", headers=tavus_headers, json=tavus_data, timeout=30)
        response.raise_for_status()

        filename = f"output_{uuid.uuid4().hex}.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"✅ Audio file saved as {filename}")
        return filename

    except requests.exceptions.RequestException as e:
        print(f"❌ TTS API error: {e}")
        return None

def upload_audio_to_host(audio_path):
    print("☁️ Uploading audio to file.io...")
    with open(audio_path, "rb") as f:
        response = requests.post("https://file.io", files={"file": f})
    if response.status_code == 200:
        url = response.json().get("link")
        print(f"✅ Uploaded to: {url}")
        return url
    else:
        print("❌ Upload failed:", response.text)
        return None


def call_tavus_lipsync(audio_url):
    lipsync_data = {
        "original_video_url": DEFAULT_VIDEO_URL,
        "source_audio_url": audio_url,
        "lipsync_name": "shop llama"
    }

    try:
        response = requests.post(TAVUS_LIPSYNC_URL, headers=tavus_headers, json=lipsync_data)
        if response.status_code == 200:
            result = response.json()
            lipsync_id = result.get("lipsync_id")
            print(f"📦 Lipsync job started: {lipsync_id}")
            return lipsync_id
        else:
            print(f"❌ Tavus LipSync error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ LipSync API error: {e}")
        return None

def poll_for_video(lipsync_id):
    poll_url = f"https://tavusapi.com/v2/lipsync/{lipsync_id}"
    headers = {"x-api-key": TAVUS_API_KEY}

    for _ in range(20):
        response = requests.get(poll_url, headers=headers)
        result = response.json()

        print("📦 Full Tavus response:", json.dumps(result, indent=2))  # 🔍 ADD THIS

        status = result.get("status")
        print(f"⏳ Status: {status}")

        if status == "completed":
            return result.get("video_url") or result.get("lipsynced_video_url")
        elif status == "failed":
            print("❌ Tavus failed to generate video.")
            return None

        time.sleep(5)

    print("⏰ Timed out waiting for Tavus video.")
    return None

def converse():
    print("🎙️ Using hardcoded MP3 for lipsync...")

    hosted_audio_url = "https://cdn.replica.tavus.io/sample-audios/f9ded6d303.mp3"

    print("🎬 Creating lipsync video...")
    lipsync_id = call_tavus_lipsync(hosted_audio_url)
    if not lipsync_id:
        return

    print("⏳ Waiting for final video from Tavus...")
    final_video_url = poll_for_video(lipsync_id)
    if final_video_url:
        print(f"✅ Your video is ready: {final_video_url}")
    else:
        print("❌ Failed to generate video")

if __name__ == "__main__":
    converse()
