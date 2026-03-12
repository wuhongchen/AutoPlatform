from modules.feishu import FeishuBitable
import json

def test_parser():
    feishu = FeishuBitable("", "", "")
    # 模拟微信 HTML 片段 (嵌套严重)
    html = """
    <section>
        <section>
            <h1>这是一个标题</h1>
        </section>
        <div class="para">
            <p>这是一段话<strong>这是加粗</strong></p>
        </div>
        <img src="test.jpg">
    </section>
    """
    blocks = feishu.html_to_docx_blocks(html)
    print(f"Parsed {len(blocks)} blocks")
    print(json.dumps(blocks, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_parser()
