import os
import requests
import json
import speech_recognition as sr
import uuid
import time
from utils.stripe_checkout import create_checkout_link

# API Keys
LLAMA_API_KEY = 'LLM|1245705104001779|zbn6HjpcOleaP0XHLL-vKw_n2Bw'
TAVUS_API_KEY = 'tvus_sk_1a2b3c4d5e6f7g8h9i0j'
DEFAULT_VIDEO_URL = "https://cdn.replica.tavus.io/sample-videos/1.mp4"

# API Endpoints
LLAMA_URL = "https://api.llama-api.com/chat/completions"
TAVUS_URL = "https://api.tavus.io/v1/tts"
TAVUS_LIPSYNC_URL = "https://api.tavus.io/v1/lipsync"

# Headers
llama_headers = {
    "Authorization": f"Bearer {LLAMA_API_KEY}",
    "Content-Type": "application/json"
}

tavus_headers = {
    "x-api-key": TAVUS_API_KEY,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg"
}

def call_llama_api(prompt):
    """Make a call to the Llama API"""
    try:
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        response = requests.post(
            LLAMA_URL,
            headers=llama_headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error response from Llama: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling Llama API: {e}")
        return None

def call_tavus_tts(text):
    """Make a call to the Tavus TTS API"""
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
        print(f"Attempting to connect to Tavus API at {TAVUS_URL}")
        print(f"Request headers: {json.dumps(tavus_headers, indent=2)}")
        print(f"Request data: {json.dumps(tavus_data, indent=2)}")
        
        response = requests.post(TAVUS_URL, headers=tavus_headers, json=tavus_data, timeout=60)
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
    """Upload audio file to file.io for hosting"""
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
    """Create a lipsync video using Tavus API"""
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
    """Poll Tavus API for video completion"""
    poll_url = f"https://tavusapi.com/v2/lipsync/{lipsync_id}"
    headers = {"x-api-key": TAVUS_API_KEY}

    for _ in range(20):
        response = requests.get(poll_url, headers=headers)
        result = response.json()

        print("📦 Full Tavus response:", json.dumps(result, indent=2))

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
    print("Welcome! Type your message and press Enter to chat with the computer. Type 'exit' or 'quit' to end.")
    while True:
        print("\nYou can type your message now:")
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
            
        print("\nThinking...")
        llama_response = call_llama_api(user_input)
        
        if llama_response and 'completion_message' in llama_response:
            generated_content = llama_response['completion_message']['content']['text']
            print(f"Llama: {generated_content}")
            
            print("\nGenerating audio...")
            mp3_file = call_tavus_tts(generated_content)
            
            if mp3_file:
                print("\nPlaying audio...")
                os.system(f"afplay {mp3_file}")  # Mac: play the audio
                
                print("\nCreating video...")
                hosted_audio_url = upload_audio_to_host(mp3_file)
                if hosted_audio_url:
                    lipsync_id = call_tavus_lipsync(hosted_audio_url)
                    if lipsync_id:
                        print("\nWaiting for video generation...")
                        video_url = poll_for_video(lipsync_id)
                        if video_url:
                            print(f"\n🎥 Your video is ready: {video_url}")
            else:
                print("(Audio generation failed)")
                
        elif "checkout" in user_input.lower():
            url = create_checkout_link()
            print(f"Go to this checkout page: {url}")
        else:
            print("(Llama did not return a response)")

if __name__ == "__main__":
    converse()
