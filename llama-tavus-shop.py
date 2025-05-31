import os
import requests
import json

# API Keys
LLAMA_API_KEY = 'LLM|1245705104001779|zbn6HjpcOleaP0XHLL-vKw_n2Bw'
TAVUS_API_KEY = '12032643152644c19e18bc16969287c3'

# API endpoints
LLAMA_URL = "https://api.llama.com/v1/chat/completions"
TAVUS_URL = "https://api.tavus.io/v1/tts"  # Updated endpoint

# Headers
llama_headers = {
    "Authorization": f"Bearer {LLAMA_API_KEY}",
    "Content-Type": "application/json"
}

tavus_headers = {
    "Authorization": f"Bearer {TAVUS_API_KEY}",
    "Content-Type": "application/json"
}

def call_llama_api(prompt):
    """Make a call to the Llama API"""
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
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Llama API: {e}")
        return None

def call_tavus_api(text_content):
    """Make a call to the Tavus API for text-to-speech"""
    try:
        # Format the data for Tavus speech API
        tavus_data = {
            "input": {
                "text": text_content
            },
            "voice": {
                "name": "en-US-Neural2-F"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0
            }
        }
        
        print("Sending request to Tavus with data:", json.dumps(tavus_data, indent=2))
        
        response = requests.post(
            TAVUS_URL, 
            headers=tavus_headers, 
            json=tavus_data,
            timeout=30
        )
        
        print(f"Tavus API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Save the audio file
            with open("output.mp3", "wb") as f:
                f.write(response.content)
            print("Audio file saved as output.mp3")
            return True
        else:
            print(f"Error response from Tavus: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error calling Tavus API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return False

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
            print("\nSpeaking...")
            success = call_tavus_api(generated_content)
            if success:
                os.system("afplay output.mp3")  # Mac: play the audio
            else:
                print("(Audio generation failed)")
        else:
            print("(Llama did not return a response)")

if __name__ == "__main__":
    converse()
