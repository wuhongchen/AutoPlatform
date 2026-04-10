#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# 直接使用你提供的Kimi API Key
KIMI_API_KEY = "sk-kimi-uCmA0mxOKbxBUk1a1HZL7tvpedhmqvdPzXkt1QjfKJiefX3kO8sjvN4Xk0RVkV6p"
KIMI_ENDPOINT = "https://api.moonshot.cn/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {KIMI_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "kimi-k2.5",
    "messages": [
        {"role": "system", "content": "你是一个测试助手，只返回简单的JSON格式"},
        {"role": "user", "content": "你好，返回一个JSON，包含字段：status=ok，message=测试成功，score=8"}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.1
}

print(f"正在测试Kimi API...")
print(f"API Key: {KIMI_API_KEY[:10]}...{KIMI_API_KEY[-10:]}")
print(f"Endpoint: {KIMI_ENDPOINT}")

try:
    resp = requests.post(KIMI_ENDPOINT, headers=headers, json=payload, timeout=30)
    print(f"\nHTTP状态码: {resp.status_code}")
    print(f"响应内容: {resp.text[:500]}")

    if resp.status_code == 200:
        res_json = resp.json()
        content = res_json['choices'][0]['message']['content']
        print(f"\n✅ API调用成功！返回内容：{content}")
    else:
        print(f"\n❌ API调用失败，状态码：{resp.status_code}")

except Exception as e:
    print(f"\n❌ 请求异常：{e}")