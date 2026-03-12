import os
import sys
from manager import AutoPlatformManager

def run_ab_test(url):
    manager = AutoPlatformManager()
    
    print("\n" + "="*50)
    print(f"🔬 开始 A/B 测试比较")
    print(f"目标 URL: {url}")
    print("="*50)
    
    # 方案 A: 标准技术博主风格
    print("\n[方案 A] 正在生成：标准技术博主...")
    res_a = manager.step_collect(url)
    if not res_a: return
    rewritten_a = manager.step_rewrite(res_a, role_key="tech_expert", model_key="volcengine")
    
    # 方案 B: XHS-Pro (逆向工程 + 双专家 + De-AI)
    print("\n[方案 B] 正在生成：XHS-Pro (拟人化爆款)...")
    rewritten_b = manager.step_rewrite(res_a, role_key="xhs", model_key="volcengine")
    
    # 结果输出
    output_path = "ab_test_result.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# A/B 测试结果比较\n\n")
        f.write(f"**原文:** {url}\n\n")
        
        f.write("## --- [方案 A] 标准技术博主 ---\n")
        f.write(f"### 标题: {rewritten_a['title']}\n\n")
        f.write(f"{rewritten_a['content']}\n\n")
        
        f.write("\n" + "="*30 + "\n\n")
        
        f.write("## --- [方案 B] XHS-Pro (去AI化爆款) ---\n")
        f.write(f"### 标题: {rewritten_b['title']}\n\n")
        f.write(f"{rewritten_b['content']}\n\n")
        
    print(f"\n✅ A/B 测试对比完成！结果已保存至: {output_path}")
    print("您可以打开该文件直观对比两者的‘人感’差异。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        test_url = "https://mp.weixin.qq.com/s/QAC_ssgNY72h3Rrgl4n9HA"
    else:
        test_url = sys.argv[1]
    
    run_ab_test(test_url)
