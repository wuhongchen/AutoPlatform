import os
import requests
import time
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def check_token_validity():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    feishu = FeishuBitable(app_id, app_secret, app_token)
    feishu._get_token()
    
    # 使用上一次成功获取的 token
    old_token = "CrSDbWrFmowiKQxKshhcXMRUnYf"
    doc_id, doc_url = feishu.create_docx("Token 有效性验证")
    print(f"📄 Doc: {doc_url}")
    
    time.sleep(5)  # 充分等待
    
    headers = {"Authorization": f"Bearer {feishu.token}", "Content-Type": "application/json"}
    append_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    
    # 1. 先用旧 token 尝试
    print(f"\n📡 尝试写入旧 docx_image token ({old_token[:8]}...):")
    payload = {"children": [{"block_type": 11, "image": {"token": old_token}}], "index": -1}
    r = requests.post(append_url, headers=headers, json=payload).json()
    print(f"  结果: code={r.get('code')}, msg={r.get('msg')}")
    
    time.sleep(2)
    
    # 2. 上传新图片，立刻写入（不等待）
    print(f"\n📡 上传新图片后立刻写入（0 秒延迟）:")
    red = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\x0dcG\x04\x00\x00\x00\x00IEND\xaeB`\x82'
    data = {'parent_type': 'docx_image', 'parent_node': doc_id, 'size': str(len(red)), 'file_name': 'test.png'}
    files = {'file': ('test.png', red, 'image/png')}
    r_up = requests.post("https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
                         headers={"Authorization": f"Bearer {feishu.token}"}, data=data, files=files).json()
    if r_up.get("code") == 0:
        new_token = r_up["data"]["file_token"]
        print(f"  上传成功 Token: {new_token}")
        
        # 立刻写入（不加 sleep）
        r_insert = requests.post(append_url, headers=headers, json={
            "children": [{"block_type": 11, "image": {"token": new_token}}], "index": -1
        }).json()
        print(f"  写入结果 (0s): code={r_insert.get('code')}")
        
        # 等 1 秒再尝试
        time.sleep(1)
        r_insert2 = requests.post(append_url, headers=headers, json={
            "children": [{"block_type": 11, "image": {"token": new_token}}], "index": -1
        }).json()  
        print(f"  写入结果 (1s): code={r_insert2.get('code')}")
        
        # 等 3 秒再尝试
        time.sleep(3)
        r_insert3 = requests.post(append_url, headers=headers, json={
            "children": [{"block_type": 11, "image": {"token": new_token}}], "index": -1
        }).json()
        print(f"  写入结果 (4s): code={r_insert3.get('code')}")
        
        # 等 10 秒再尝试
        time.sleep(10)
        r_insert4 = requests.post(append_url, headers=headers, json={
            "children": [{"block_type": 11, "image": {"token": new_token}}], "index": -1
        }).json()
        print(f"  写入结果 (14s): code={r_insert4.get('code')}")

if __name__ == "__main__":
    check_token_validity()
