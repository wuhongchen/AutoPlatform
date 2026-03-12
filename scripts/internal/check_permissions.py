import os
import requests
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def check_permissions():
    """验证飞书应用的文档写入权限"""
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    feishu = FeishuBitable(app_id, app_secret, "")
    feishu._get_token()
    
    headers = {"Authorization": f"Bearer {feishu.token}"}
    
    # 1. 查看当前 token 代表的应用信息
    r = requests.get(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        headers={"Content-Type": "application/json"},
        json={"app_id": app_id, "app_secret": app_secret}
    )
    print(f"Token 获取: {'✅' if feishu.token else '❌'}")
    
    # 2. 测试能否写入文档（直接创建并尝试简单 block）
    import time
    doc_resp = requests.post(
        "https://open.feishu.cn/open-apis/docx/v1/documents",
        headers={**headers, "Content-Type": "application/json"},
        json={"title": "权限验证"}
    ).json()
    
    if doc_resp.get("code") != 0:
        print(f"❌ 无法创建文档: {doc_resp}")
        return
    
    doc_id = doc_resp["data"]["document"]["document_id"]
    time.sleep(5)
    
    # 测试写入文本
    r_text = requests.post(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
        headers={**headers, "Content-Type": "application/json"},
        json={"children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "权限测试"}}]}}], "index": -1}
    ).json()
    print(f"文本写入权限: {'✅' if r_text.get('code') == 0 else '❌ code=' + str(r_text.get('code'))}")
    
    # 测试写入图片（上传后插入）
    red = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\x0dcG\x04\x00\x00\x00\x00IEND\xaeB`\x82'
    r_up = requests.post(
        "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
        headers={"Authorization": f"Bearer {feishu.token}"},
        data={"parent_type": "docx_image", "parent_node": doc_id, "size": str(len(red)), "file_name": "perm_test.png"},
        files={"file": ("perm_test.png", red, "image/png")}
    ).json()
    
    if r_up.get("code") == 0:
        token = r_up["data"]["file_token"]
        time.sleep(2)
        r_img = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
            headers={**headers, "Content-Type": "application/json"},
            json={"children": [{"block_type": 11, "image": {"token": token}}], "index": -1}
        ).json()
        print(f"图片块写入权限: {'✅' if r_img.get('code') == 0 else '❌ code=' + str(r_img.get('code'))}")
        
        if r_img.get("code") == 1770001:
            print("\n⚠️  确认：这是权限问题！")
            print("👉 请前往飞书开放平台 → 应用管理 → 权限管理，确保已开启：")
            print("   - docx:document:write（文档写入）")
            print("   - drive:drive.media:write（媒体上传）")
            print("   - docs:doc:write（旧版文档写入，也建议开启）")
            print("\n开放平台地址: https://open.feishu.cn/app")

if __name__ == "__main__":
    check_permissions()
