#!/usr/bin/env python3
import requests

# 直接使用你提供的火山API信息
VOLC_API_KEY = "fa60d350-6328-499a-82da-2d9c31d18e32"
VOLC_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
VOLC_MODEL = "doubao-seed-2-0-pro-260215"

headers = {
    "Authorization": f"Bearer {VOLC_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": VOLC_MODEL,
    "messages": [
        {"role": "system", "content": "你是一个测试助手，只返回简单的JSON格式"},
        {"role": "user", "content": "你好，返回一个JSON，包含字段：status=ok，message=测试成功，score=8"}
    ],
    "temperature": 0.1
}

print(f"正在测试火山API...")
print(f"API Key: {VOLC_API_KEY}")
print(f"Endpoint: {VOLC_ENDPOINT}")
print(f"Model: {VOLC_MODEL}")

try:
    resp = requests.post(VOLC_ENDPOINT, headers=headers, json=payload, timeout=30)
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