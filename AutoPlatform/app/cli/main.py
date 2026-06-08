"""
CLI入口
"""
import asyncio
import json
import typer
from rich.console import Console
from rich.table import Table
from app.core import AppManager

app = typer.Typer(help="AutoPlatform CLI")
console = Console()
manager = AppManager()


def _print_json(data):
    console.print_json(data=json.dumps(data, ensure_ascii=False, default=str))

@app.command()
def account_create(
    name: str = typer.Option(..., "--name", "-n", help="账户名称"),
    account_id: str = typer.Option(..., "--id", "-i", help="账户ID"),
    appid: str = typer.Option("", "--appid", help="微信AppID"),
    secret: str = typer.Option("", "--secret", help="微信AppSecret")
):
    """创建账户"""
    account = manager.create_account(
        name=name,
        account_id=account_id,
        wechat_appid=appid,
        wechat_secret=secret
    )
    console.print(f"[green]账户创建成功: {account.name}[/green]")

@app.command()
def account_list():
    """列出账户"""
    accounts = manager.list_accounts()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("名称")
    table.add_column("状态")
    
    for acc in accounts:
        table.add_row(acc.account_id, acc.name, acc.status.value)
    
    console.print(table)

@app.command()
def collect(
    url: str = typer.Option(..., "--url", "-u", help="文章URL"),
    account: str = typer.Option("default", "--account", "-a", help="账户ID")
):
    """采集灵感"""
    console.print(f"[blue]正在采集: {url}[/blue]")
    record = asyncio.run(manager.collect_inspiration(url, account))
    console.print(f"[green]采集完成: {record.title}[/green]")
    console.print(f"AI评分: {record.ai_score}")

@app.command()
def rewrite(
    article_id: str = typer.Option(..., "--id", "-i", help="文章ID"),
    style: str = typer.Option("tech_expert", "--style", "-s", help="改写风格"),
    no_ref: bool = typer.Option(False, "--no-ref", help="不引用灵感库"),
    instructions: str = typer.Option("", "--instructions", help="额外指令")
):
    """改写文章"""
    console.print(f"[blue]正在改写: {article_id} (风格: {style})[/blue]")
    article = asyncio.run(manager.rewrite_article(
        article_id,
        style=style,
        use_references=not no_ref,
        custom_instructions=instructions if instructions else None
    ))
    console.print(f"[green]改写完成: {article.source_title}[/green]")
    console.print(f"  使用风格: {article.rewrite_style}")
    if article.rewrite_references:
        console.print(f"  引用参考: {len(article.rewrite_references)} 篇")

@app.command()
def styles():
    """列出改写风格预设"""
    presets = manager.get_style_presets()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("名称")
    table.add_column("描述")
    table.add_column("语气")
    table.add_column("风格")
    
    for preset in presets:
        table.add_row(
            preset["id"],
            preset["name"],
            preset["description"][:30] + "..." if len(preset["description"]) > 30 else preset["description"],
            preset["tone"],
            preset["style"]
        )
    
    console.print(table)

@app.command()
def publish(
    article_id: str = typer.Option(..., "--id", "-i", help="文章ID"),
    template: str = typer.Option("default", "--template", "-t", help="模板名称")
):
    """发布文章"""
    console.print(f"[blue]正在发布: {article_id} (使用 {template} 模板)[/blue]")
    article = asyncio.run(manager.publish_article(article_id, template=template))
    console.print(f"[green]发布完成: {article.wechat_draft_id}[/green]")

@app.command()
def templates():
    """列出可用模板"""
    templates = manager.get_templates()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("名称")
    table.add_column("描述")
    
    for name, config in templates.items():
        table.add_row(name, config.description)
    
    console.print(table)

@app.command()
def preview(
    template: str = typer.Option("default", "--template", "-t", help="模板名称"),
    output: str = typer.Option("preview.html", "--output", "-o", help="输出文件")
):
    """预览模板效果"""
    from app.templates import TemplateRegistry
    
    tpl = TemplateRegistry.create_instance(template)
    if not tpl:
        console.print(f"[red]模板 {template} 不存在[/red]")
        return
    
    # 示例内容
    html = tpl.render(
        title="示例文章标题",
        content="""
        <h2>这是副标题</h2>
        <p>这是一段示例内容，用于预览模板效果。你可以看到不同模板的排版风格差异。</p>
        <h3>小标题</h3>
        <p>模板系统支持多种风格：</p>
        <ul>
            <li>经典默认 - 适合大多数场景</li>
            <li>极简风格 - 专注内容本身</li>
            <li>科技风格 - 深色现代风格</li>
            <li>商务风格 - 专业正式风格</li>
        </ul>
        <blockquote>这是一段引用文字</blockquote>
        """,
        author="AutoPlatform"
    )
    
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    
    console.print(f"[green]预览文件已生成: {output}[/green]")
    console.print(f"[blue]请在浏览器中打开查看 {template} 模板效果[/blue]")

@app.command()
def pipeline(
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    batch: int = typer.Option(3, "--batch", "-b", help="批处理大小"),
    style: str = typer.Option(None, "--style", "-s", help="改写风格预设"),
    template: str = typer.Option("default", "--template", "-t", help="发布模板")
):
    """运行流水线"""
    console.print(f"[blue]开始处理流水线...[/blue]")
    console.print(f"  账户: {account} | 批次: {batch} | 风格: {style or '默认'} | 模板: {template}")
    asyncio.run(manager.process_pipeline(
        account_id=account,
        batch_size=batch,
        style=style,
        template=template
    ))
    console.print(f"[green]流水线处理完成[/green]")

@app.command()
def stats(
    account: str = typer.Option(None, "--account", "-a", help="账户ID")
):
    """查看统计"""
    stats = manager.get_stats(account)
    console.print(stats)


@app.command()
def wechat_ingest_status(
    account: str = typer.Option("default", "--account", "-a", help="账户ID")
):
    """查看公众号登录态采集状态"""
    _print_json(manager.wechat_ingest_status(account))


@app.command()
def wechat_ingest_login(
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    wait: bool = typer.Option(False, "--wait", help="是否同步等待登录完成"),
):
    """触发公众号后台扫码登录"""
    _print_json(manager.wechat_ingest_login(account, wait=wait))


@app.command()
def wechat_ingest_search_mp(
    keyword: str = typer.Option(..., "--keyword", "-k", help="公众号关键词"),
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    limit: int = typer.Option(10, "--limit", help="返回候选数量"),
):
    """检索公众号"""
    _print_json(manager.wechat_ingest_search_mp(account, keyword=keyword, limit=limit))


@app.command()
def wechat_ingest_add_mp(
    keyword: str = typer.Option(..., "--keyword", "-k", help="公众号关键词"),
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    pick: int = typer.Option(1, "--pick", "-p", help="选择第几个候选"),
    limit: int = typer.Option(10, "--limit", help="检索候选数量"),
):
    """搜索并关注公众号"""
    _print_json(manager.wechat_ingest_add_mp(account, keyword=keyword, pick=pick, limit=limit))


@app.command()
def wechat_ingest_list_mp(
    account: str = typer.Option("default", "--account", "-a", help="账户ID")
):
    """查看已关注公众号"""
    _print_json(manager.wechat_ingest_list_mps(account))


@app.command()
def wechat_ingest_pull_articles(
    mp_id: str = typer.Option(..., "--mp-id", help="公众号ID"),
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    pages: int = typer.Option(1, "--pages", help="拉取页数"),
    with_content: bool = typer.Option(False, "--with-content", help="是否同时抓正文"),
):
    """拉取公众号文章列表"""
    _print_json(
        manager.wechat_ingest_pull_articles(
            account,
            mp_id=mp_id,
            pages=pages,
            with_content=with_content,
        )
    )


@app.command()
def wechat_ingest_sync(
    account: str = typer.Option("default", "--account", "-a", help="账户ID"),
    mp_id: str = typer.Option("", "--mp-id", help="公众号ID，不传则同步最近文章"),
    limit: int = typer.Option(20, "--limit", help="同步上限"),
):
    """将公众号文章同步到素材库"""
    _print_json(manager.wechat_ingest_sync_inspirations(account, mp_id=mp_id, limit=limit))

if __name__ == "__main__":
    app()
