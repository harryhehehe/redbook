"""CLI entrypoint."""
from __future__ import annotations
import json
import sys

import click

from . import data, recommender, prompt_builder, llm_client, renderer


@click.group()
def cli():
    """小红书数学家教帖子生成器 MVP demo"""
    pass


@cli.command()
@click.option("--topic", "-t", required=True, help="帖子主题，如'二次函数'")
@click.option("--audience", "-a", default="parent", type=click.Choice(["student", "parent", "both"]))
@click.option("--template", "-T", "template_id", default=None, help="强制指定模板 ID（默认自动推荐）")
@click.option("--dry-run", is_flag=True, help="只打印 prompt，不调 LLM")
@click.option("--titles/--no-titles", default=True, help="是否生成 5 个备选标题")
@click.option("--save-json", type=click.Path(), default=None, help="保存原始 block JSON 到文件")
def generate(topic, audience, template_id, dry_run, titles, save_json):
    """根据主题生成一篇小红书帖子。"""
    click.secho(f"\n🎯 主题：{topic}  受众：{audience}", fg="cyan", bold=True)

    rec = recommender.recommend(topic, audience)
    click.echo("\n📊 模板推荐：")
    for r in rec["templates"]:
        click.echo(f"  - {r['template_id']}  分数 {r['score']}  命中范例 {r['matched_posts']}")

    chosen = template_id or rec["templates"][0]["template_id"]
    click.secho(f"\n✅ 选用模板：{chosen}", fg="green")
    click.echo(f"📚 few-shot 范例：{[p['id'] + ' ' + p['title'] for p in rec['few_shot_posts'][:3]]}")

    system_prompt, user_prompt = prompt_builder.build_prompt(
        topic=topic, audience=audience, template_id=chosen,
        few_shot_posts=rec["few_shot_posts"],
    )

    if dry_run:
        click.secho("\n--- SYSTEM PROMPT ---", fg="yellow")
        click.echo(system_prompt)
        click.secho("\n--- USER PROMPT ---", fg="yellow")
        click.echo(user_prompt)
        return

    click.echo("\n⏳ 调用千问生成中...")
    try:
        result = llm_client.generate_blocks(system_prompt, user_prompt)
    except llm_client.LLMError as e:
        click.secho(f"\n❌ {e}", fg="red")
        sys.exit(1)

    if save_json:
        with open(save_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        click.echo(f"📄 原始 JSON 已保存：{save_json}")

    body = renderer.render(result["blocks"])
    click.secho("\n========== 📝 帖子正文 ==========\n", fg="magenta", bold=True)
    click.echo(body)
    click.secho("\n=================================\n", fg="magenta")

    if titles:
        click.echo("⏳ 生成备选标题...")
        try:
            ts = llm_client.generate_titles(body)
            click.secho("\n🏷️  备选标题：", fg="cyan", bold=True)
            for t in ts:
                click.echo(f"  [{t.get('style')}] {t.get('text')}")
        except Exception as e:
            click.secho(f"标题生成失败：{e}", fg="yellow")


@cli.command()
def info():
    """显示已加载的模板和范例数。"""
    click.echo(f"模板数：{len(data.templates())}")
    click.echo(f"范例帖：{len(data.posts())}")
    click.echo(f"引流资料：{len(data.libraries()['lead_magnet_examples'])}")
    click.echo("\n模板列表：")
    for t in data.templates():
        click.echo(f"  - {t['id']}  {t['name']}  ({t['series']})")


if __name__ == "__main__":
    cli()
