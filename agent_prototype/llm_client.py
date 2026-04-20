import os
import requests 

BASE_URL = "https://api.bltcy.ai"
API_KEY = "sk-if5ozW27udBQVVuHtRKoALsbc4Ob0qu7RxEaDGLniCIGVr1U"
MODEL = "MiniMax-M2.5-lightning"


def call_llm(messages):
    url=f"{BASE_URL}/v1/chat/completions"
    headers ={
        "Accept":"application/json",
        "Authorization":f"Bearer {API_KEY}",
        "Content-Type":"application/json"
    }
    payload={
        "model":MODEL,
        "messages":messages,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
