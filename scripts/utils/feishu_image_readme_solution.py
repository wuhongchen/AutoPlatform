
import requests
import json
import os
import time
import subprocess

# 飞书凭证（从环境变量读取）
APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

def get_tenant_access_token():
    if not APP_ID or not APP_SECRET:
        print("❌ 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")
        return None
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        resp = requests.post(url, json=payload).json()
        return resp.get("tenant_access_token")
    except: return None

def test_fixed_readme_logic():
    token = get_tenant_access_token()
    if not token: return
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    
    document_id = "NKswdPvhEoMwMbxXZFMctcU8nuh"
    
    print(f"🚀 尝试修复版 README 方案 (API 路径: 创建文档 children)...")

    # 修复 1: 确保 block_type 对应官方字段名
    # 在插入 children 时，block_type=11 对应的 Data 字段必须是 "image"
    create_block_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children"
    block_payload = {
        "children": [
            {
                "block_type": 11,
                "image": {} # 此处必须有 key 为 image 的空字典
            }
        ],
        "index": -1
    }
    
    print("1️⃣ 正在创建图片占位块...")
    resp = requests.post(create_block_url, headers=headers, json=block_payload).json()
    if resp.get("code") != 0:
        print(f"❌ 创建失败: {resp}")
        # 如果还是报 1770001，可能是 image 块不能通过此方式创建空块
        # 我们换一种方式：插入一条文本看权限
        return
    
    new_block_id = resp["data"]["children"][0]["block_id"]
    print(f"✅ 图片占位块 ID: {new_block_id}")

    # 2️⃣ 转码图片
    img_url = "https://mmbiz.qpic.cn/mmbiz_png/vI9nYe94fsGxu3P5YibTO899okS0X9WaLmQCtia4U8Eu1xWCz9t8Qtq9PH6T1bTcxibiaCIkGzAxpeRkRFYqibVmwSw/640?wx_fmt=other&wxfrom=5&wx_lazy=1&wx_co=1&tp=webp"
    webp_path = "/tmp/readme_test.webp"
    png_path = "/tmp/readme_test.png"
    img_data = requests.get(img_url).content
    with open(webp_path, 'wb') as f: f.write(img_data)
    subprocess.run(["sips", "-s", "format", "png", webp_path, "--out", png_path], capture_output=True)

    # 3️⃣ 上传素材，关键：parent_type="docx_image", parent_node=block_id
    upload_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    with open(png_path, 'rb') as f:
        content = f.read()
        upload_data = {
            'parent_type': 'docx_image',
            'parent_node': new_block_id,
            'size': str(len(content)),
            'file_name': 'readme_test.png'
        }
        upload_files = {'file': ('readme_test.png', content, 'image/png')}
        print("3️⃣ 正在上传图片素材 (parent_type='docx_image')...")
        upl_resp = requests.post(upload_url, headers={"Authorization": f"Bearer {token}"}, data=upload_data, files=upload_files).json()
        
        if upl_resp.get("code") != 0:
            print(f"❌ 素材上传失败: {upl_resp}")
            return
        
        file_token = upl_resp["data"]["file_token"]
        print(f"✅ 素材上传成功: {file_token}")

    # 4️⃣ 关联
    update_block_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{new_block_id}"
    update_payload = {
        "replace_image": {
            "token": file_token
        }
    }
    print("4️⃣ 正在执行关联更新...")
    # 注意：更新 Block 内容通常使用 PATCH 接口
    final_resp = requests.patch(update_block_url, headers=headers, json=update_payload).json()
    print(f"📊 最终结果: {json.dumps(final_resp, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    test_fixed_readme_logic()
