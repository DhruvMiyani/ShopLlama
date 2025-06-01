from utils.tavus import tts
from agents.checkout_agent import run_agent
import os, subprocess, json

session = {"messages": [], "state": {}}

print("Type anything – 'checkout' flow is handled automatically. 'quit' to exit.")
while True:
    user = input("\nYou: ")
    if user.lower() in {"quit", "exit"}:
        break

    print("Thinking …")
    reply, session = run_agent(session, user)

    msg = reply["choices"][0]["message"]
    if msg.get("content"):
        print(f"\nShopLlama: {msg['content']}")
        print("Speaking …")
        mp3 = tts(msg["content"])
        subprocess.run(["afplay", str(mp3)])   # macOS; replace with 'ffplay' cross-platform 