
import requests
import json
import os
import subprocess
import time

def get_token():
    ID = "cli_a85b1afbbcb99013"
    SECRET = "WJ7zZacqrSqUM6HpIpE0BegKJVmDbeN6"
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        resp = requests.post(url, json={"app_id": ID, "app_secret": SECRET}).json()
        return resp.get("tenant_access_token")
    except:
        return None

def test_conversion_and_upload():
    token = get_token()
    if not token:
        print("❌ 无法获取 Token")
        return

    # 1. 下载原始 WebP
    url = "https://mmbiz.qpic.cn/mmbiz_png/vI9nYe94fsGxu3P5YibTO899okS0X9WaLmQCtia4U8Eu1xWCz9t8Qtq9PH6T1bTcxibiaCIkGzAxpeRkRFYqibVmwSw/640?wx_fmt=other&wxfrom=5&wx_lazy=1&wx_co=1&tp=webp#imgIndex=2"
    webp_path = "/tmp/image_to_convert.webp"
    png_path = "/tmp/converted_image.png"
    
    print(f"📥 正在下载: {url}")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://mp.weixin.qq.com/"}
    img_data = requests.get(url, headers=headers).content
    with open(webp_path, 'wb') as f:
        f.write(img_data)

    # 2. 使用 macOS 自带的 sips 进行转码 (WebP -> PNG)
    print("🔄 正在使用 sips 进行转码...")
    try:
        subprocess.run(["sips", "-s", "format", "png", webp_path, "--out", png_path], check=True, capture_output=True)
        print(f"✅ 转码成功: {png_path}")
    except Exception as e:
        print(f"❌ 转码失败: {e}")
        return

    # 3. 上传到飞书 Docx 空间
    # 使用之前确认的文档 ID
    document_id = "NKswdPvhEoMwMbxXZFMctcU8nuh" 
    upload_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    
    with open(png_path, 'rb') as f:
        png_content = f.read()
        files = {
            'file': (os.path.basename(png_path), png_content, 'image/png')
        }
        data = {
            'parent_type': 'docx',
            'parent_node': document_id,
            'size': str(len(png_content)),
            'file_name': os.path.basename(png_path)
        }
        
        print(f"🚀 正在上传至飞书 (docx 模式)...")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.post(upload_url, headers=headers, data=data, files=files).json()
            print(f"📊 上传响应: {json.dumps(resp, indent=2, ensure_ascii=False)}")
            
            if resp.get("code") == 0:
                print(f"✨ 上传成功! File Token: {resp['data']['file_token']}")
            else:
                print(f"❌ 上传失败: {resp.get('msg')}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_conversion_and_upload()
