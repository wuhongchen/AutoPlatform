
import requests

def debug_fetch(url):
    print(f"🔍 正在抓取 URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mp.weixin.qq.com/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        print(f"✅ 状态码: {resp.status_code}")
        print("--- 响应头 ---")
        for k, v in resp.headers.items():
            print(f"{k}: {v}")
        
        content = resp.content
        print("\n--- 元数据 ---")
        print(f"实际字节长度 (len): {len(content)}")
        print(f"Content-Type (Header): {resp.headers.get('Content-Type')}")
        print(f"魔数 (前16字节): {content[:16].hex()}")
        
        # 简单判定
        if content.startswith(b'\x89PNG'):
            print("判定结果: PNG 图片")
        elif b'JFIF' in content[:20] or b'Exif' in content[:20] or content.startswith(b'\xff\xd8'):
            print("判定结果: JPEG 图片")
        elif content.startswith(b'RIFF') and b'WEBP' in content[8:16]:
            print("判定结果: WebP 图片")
        elif content.startswith(b'GIF8'):
            print("判定结果: GIF 图片")
        else:
            print("判定结果: 未知或非标准格式")
            
    except Exception as e:
        print(f"❌ 抓取异常: {e}")

if __name__ == "__main__":
    sample_url = "https://mmbiz.qpic.cn/mmbiz_png/vI9nYe94fsGxu3P5YibTO899okS0X9WaLmQCtia4U8Eu1xWCz9t8Qtq9PH6T1bTcxibiaCIkGzAxpeRkRFYqibVmwSw/640?wx_fmt=other&wxfrom=5&wx_lazy=1&wx_co=1&tp=webp#imgIndex=2"
    debug_fetch(sample_url)
