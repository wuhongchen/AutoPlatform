from duckduckgo_search import DDGS
import time

class ContentSearchAgent:
    """
    全网内容搜寻代理 (Discovery Agent)
    目标：根据关键词寻找高质量内容链接
    """
    def __init__(self, max_results=5):
        self.max_results = max_results

    def search_topics(self, keyword):
        """全网精准检索爆款或深度内容"""
        print(f"🕵️ 正在全网搜寻关于 '{keyword}' 的内容...")
        try:
            with DDGS() as ddgs:
                # 针对深度调研进行过滤 (包含公众号、知乎、行业媒体)
                results = ddgs.text(
                    keyword, 
                    region="cn-zh", 
                    safesearch="off", 
                    timelimit="m", # 月度内容：保证时效性
                    max_results=self.max_results
                )
                
                links = [r['href'] for r in results if r.get('href')]
                print(f"   ✅ 成功找到 {len(links)} 个相关信源链接")
                return links
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []

class DiscoverProcessor:
    """
    多信源调研总结引擎 (Content Aggregator)
    目标：多篇变一篇，产出深度综述
    """
    def __init__(self, client):
        self.client = client

    def fuse_and_summarize(self, keyword, multi_articles):
        """将多篇文章的内容拼接并进行深度综述"""
        print(f"🧠 [Discovery] 正在对 {len(multi_articles)} 篇采集内容进行跨时空深度融合...")
        
        # 提取各个信源的精髓
        fusion_input = ""
        for i, art in enumerate(multi_articles):
            fusion_input += f"--- 信源 {i+1}: {art['title']} ---\n{art['content_raw'][:1500]}\n\n"

        prompt = f"""
你是一位顶尖的“首席调研员”。请针对选题关键词【{keyword}】，对以下搜集到的多份参考内容进行全网综述。

**搜集到的信源内容:**
{fusion_input}

**【全网调研总结指令】**
1. **深度提炼：** 不要只是简单的摘要，要通过多篇内容的重合与冲突点，总结出该选题的【当前现状】、【核心争议】和【专家共识】。
2. **逻辑重构：** 产出一篇结构清晰的长文（1500字以上）。
3. **结构要求：**
   - [选题背景]：为什么这个选题现在火？
   - [多方观点对照]：A 媒体认为... B 技术专家认为...
   - [核心洞察]：基于多篇内容，提炼出 3 个不为人知的深度结论。
   - [未来建议]：对关注该话题的读者的建议。
4. **格式美观：** 包含标准的 Markdown 或 HTML 样式排版。

**请输出这篇文章的【深度综述版】。**
"""
        resp = self.client.chat.completions.create(
            model="doubao-seed-2-0-pro-260215",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        
        return resp.choices[0].message.content
