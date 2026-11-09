import os
import requests
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated")

def test():
    print(f"Testing connection to {LM_STUDIO_URL} with model {MODEL_NAME}...")
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "Привет! Ответь одним словом: 'Работает'."}],
        "max_tokens": 20
    }
    try:
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        if r.status_code == 200:
            print("✅ Success! Response:")
            print(r.json()["choices"][0]["message"]["content"])
        else:
            print(f"❌ Error: Status code {r.status_code}")
            print(r.text)
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test()
