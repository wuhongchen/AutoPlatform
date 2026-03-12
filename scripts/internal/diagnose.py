import os
import requests
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def diagnose():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    feishu = FeishuBitable(app_id, app_secret, app_token)
    feishu._get_token()
    
    # 1. 诊断图片下载
    test_urls = [
        "https://mmbiz.qpic.cn/sz_mmbiz_png/6YibKNmDYvuEXf3bL5bOZSuoVTHeByM1QY8OpxXsticWnNo1DribshW9icxG0wOiapf1m2W99yHia5xibWiaU92CiaibYf8w/640?wx_fmt=png",
        "https://mmbiz.qpic.cn/sz_mmbiz_png/6YibKNmDYvuceHiaiacic1vGia7/640?wx_fmt=png"  # 残缺 URL
    ]
    
    print("=== 图片下载诊断 ===")
    for url in test_urls:
        img = feishu._download_image(url)
        if img:
            print(f"✅ 下载成功: {url[:60]}... 大小: {len(img)} bytes, 前4字节: {img[:4]}")
        else:
            print(f"❌ 下载失败: {url[:60]}...")
    
    # 2. 诊断 99992402: 单独测试一个新文档写入简单文本
    print("\n=== 文档写入诊断 ===")
    import time
    doc_id, doc_url = feishu.create_docx("诊断测试")
    print(f"Doc: {doc_id}")
    
    time.sleep(5)  # 等待5秒，较长等待
    
    append_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    headers = {"Authorization": f"Bearer {feishu.token}", "Content-Type": "application/json"}
    
    # 尝试写文本
    payload = {"children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "测试文本"}}]}}], "index": -1}
    r = requests.post(append_url, headers=headers, json=payload).json()
    print(f"文本插入结果: {r.get('code')}, {r.get('msg')}")
    
    # 3. 诊断：检查 token 是否过期
    time.sleep(2)
    r2 = requests.post(append_url, headers=headers, json=payload).json()
    print(f"第二次插入结果: {r2.get('code')}, {r2.get('msg')}")

if __name__ == "__main__":
    diagnose()
