import time
from core.manager import AutoPlatformManager

urls = [
    "https://mp.weixin.qq.com/s/SqB9llfkT2o8x4v_LX-Ang",
    "https://mp.weixin.qq.com/s/AEQNYbXW_KvqXkt2ywz7aw",
    "https://mp.weixin.qq.com/s/fCgPwVus-Rg_ooGdBlvNPA",
    "https://mp.weixin.qq.com/s/qqmkuVP7vXnu_AxIqL_a9g"
]

def batch_process():
    manager = AutoPlatformManager()
    role = "tech_expert"
    model = "volcengine"
    
    print(f"🚀 开始批量处理 {len(urls)} 篇文章...")
    
    for i, url in enumerate(urls):
        print(f"\n项目 {i+1}/{len(urls)}")
        try:
            manager.run_with_params(url, role, model)
            print(f"✅ 第 {i+1} 篇处理完成")
        except Exception as e:
            print(f"❌ 第 {i+1} 篇处理失败: {e}")
        
        # 稍微间隔一下，避免请求过频
        if i < len(urls) - 1:
            print("😴 等待 10 秒后继续下一篇...")
            time.sleep(10)

    print("\n✨ 批量处理任务全部结束！")

if __name__ == "__main__":
    batch_process()
