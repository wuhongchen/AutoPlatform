import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("VOLC_ARK_API_KEY")
model = os.getenv("VOLC_ARK_MODEL_ID")
endpoint = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Hi, who are you?"}
    ]
}

print(f"Testing with Model: {model}")
print(f"Endpoint: {endpoint}")
print(f"Key mask: {api_key[:6]}...{api_key[-4:]}")

try:
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
