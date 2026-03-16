import re

remarks = "AI 已生成草稿：https://www.feishu.cn/docx/ZJZ3dQg5Do2mwTxUwhKccZCOnxg"
doc_link = "【AI改后稿】别再折腾OpenClaw了！这款免费AI原生浏览器，能帮你搞定80%网页端重复工作"

def get_token(fields):
    doc_link = fields.get("改后文档链接", "")
    remarks = fields.get("备注", "")
    
    for text in [str(doc_link), str(remarks)]:
        match = re.search(r'([a-zA-Z0-9]{27,})', text)
        if match:
            return match.group(1)
            
    return None

print(get_token({"改后文档链接": doc_link, "备注": remarks}))
