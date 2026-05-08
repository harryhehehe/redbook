"""Streamlit Web UI for the Xiaohongshu post generator."""
from __future__ import annotations
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from app import data, recommender, prompt_builder, llm_client, renderer, lead_magnet_gen, storage

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="小红书帖子生成器",
    page_icon="📝",
    layout="wide",
)

# ---------- 密码门（仅当配置了 APP_PASSWORD 时生效）----------
def _get_app_password() -> str:
    pwd = os.getenv("APP_PASSWORD", "")
    if not pwd:
        try:
            pwd = st.secrets.get("APP_PASSWORD", "")
        except Exception:
            pwd = ""
    return pwd


def _check_password():
    expected = _get_app_password()
    if not expected:
        return  # 未配置密码 → 跳过门禁（本地开发友好）
    if st.session_state.get("auth_ok"):
        return
    st.markdown("## 🔒 请输入访问密码")
    st.caption("本应用仅供授权用户使用")
    pwd = st.text_input("密码", type="password", key="_pwd_input",
                        label_visibility="collapsed", placeholder="请输入访问密码")
    col_a, col_b = st.columns([1, 5])
    with col_a:
        ok = st.button("进入", type="primary", use_container_width=True)
    if ok:
        if pwd == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    st.stop()


_check_password()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("⚙️ 配置")

    saved_key = os.getenv("DASHSCOPE_API_KEY", "")
    api_key = st.text_input(
        "通义千问 API Key (DashScope)",
        value="" if not saved_key or saved_key.startswith("sk-xxx") else saved_key,
        type="password",
        help="获取：https://dashscope.console.aliyun.com/apiKey",
    )
    if api_key:
        os.environ["DASHSCOPE_API_KEY"] = api_key

    model = st.selectbox(
        "模型",
        ["qwen-plus", "qwen-max", "qwen-turbo"],
        index=["qwen-plus", "qwen-max", "qwen-turbo"].index(os.getenv("QWEN_MODEL", "qwen-plus")),
        help="qwen-plus 性价比最高；qwen-max 更强但贵；qwen-turbo 最便宜",
    )
    os.environ["QWEN_MODEL"] = model

    st.divider()
    st.caption(f"📚 模板：{len(data.templates())} 套")
    st.caption(f"📑 范例：{len(data.posts())} 篇")
    st.caption(f"🎁 引流资料：{len(data.libraries()['lead_magnet_examples'])} 个")

    with st.expander("📋 模板列表"):
        for t in data.templates():
            st.write(f"**{t['id']}** {t['name']} · _{t['series']}_")
            st.caption(t["use_case"])

# ---------- Main ----------
st.title("📝 小红书数学家教帖子生成器")
st.caption("输入主题 → AI 生成结构化帖子 → 你微调每个 block → 一键复制")

page = st.radio(
    "功能",
    ["✏️ 生成帖子", "🎁 生成引流资料 PDF", "📚 历史记录"],
    horizontal=True,
    label_visibility="collapsed",
)

# ============================================================
# 📚 历史记录页
# ============================================================
if page == "📚 历史记录":
    st.subheader("📚 历史记录")
    s = storage.stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 帖子数", s["posts"])
    c2.metric("📄 PDF 数", s["pdfs"])
    c3.metric("💾 PDF 总大小", f"{s['pdf_total_bytes']/1024/1024:.1f} MB")
    with c4:
        st.write("")
        if s["posts"] + s["pdfs"] > 0:
            st.download_button(
                "📦 全部导出 ZIP",
                data=storage.export_zip(),
                file_name=f"redbook_archive_{__import__('time').strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True,
            )

    st.caption("💡 Streamlit Cloud 上 archive.db 在重新部署（git push）时会被重置，建议定期点【全部导出 ZIP】备份到本地。EXE 版本则永久保留。")

    tab_p, tab_d = st.tabs(["📝 帖子历史", "📄 PDF 历史"])

    with tab_p:
        kw = st.text_input("🔍 搜索（标题或正文）", key="hp_kw")
        rows = storage.list_posts(kw)
        if not rows:
            st.info("暂无帖子记录" if not kw else "没有匹配的帖子")
        for r in rows:
            label = f"#{r['id']:04d} · {r['created_at']} · 【{r['topic']}】 · {r['mode']}/{r['template_id'] or '-'}"
            with st.expander(label):
                full = storage.get_post(r["id"])
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    st.download_button(
                        "📥 下载 .txt",
                        data=full["body_text"],
                        file_name=f"post_{r['id']:04d}_{r['topic'][:30]}.txt",
                        mime="text/plain",
                        key=f"dlp_{r['id']}",
                    )
                with col_b:
                    st.download_button(
                        "📥 下载 JSON",
                        data=full["blocks_json"],
                        file_name=f"post_{r['id']:04d}.json",
                        mime="application/json",
                        key=f"dlpj_{r['id']}",
                    )
                with col_c:
                    if st.button("🗑️ 删除", key=f"delp_{r['id']}", type="secondary"):
                        storage.delete_post(r["id"])
                        st.rerun()

                st.caption(
                    f"受众：{full['audience']}　|　模式：{full['mode']}　|　模板：{full['template_id'] or '自由'}"
                    + (f"　|　额外要求：{full['extra_notes']}" if full["extra_notes"] else "")
                )
                st.text_area("正文", full["body_text"], height=300, key=f"pview_{r['id']}")

    with tab_d:
        kw2 = st.text_input("🔍 搜索（关键词或资料名）", key="hd_kw")
        rows = storage.list_pdfs(kw2)
        if not rows:
            st.info("暂无 PDF 记录" if not kw2 else "没有匹配的 PDF")
        for r in rows:
            label = f"#{r['id']:04d} · {r['created_at']} · 【{r['keyword']}】《{r['resource_name']}》 · {r['size']//1024} KB"
            with st.expander(label):
                full = storage.get_pdf(r["id"])
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.download_button(
                        "📥 下载 PDF",
                        data=full["pdf_blob"],
                        file_name=f"{r['resource_name']}_{r['id']:04d}.pdf",
                        mime="application/pdf",
                        type="primary",
                        key=f"dld_{r['id']}",
                    )
                with col_b:
                    if st.button("👀 预览", key=f"pvd_{r['id']}"):
                        st.session_state[f"_pv_{r['id']}"] = True
                with col_c:
                    if st.button("🗑️ 删除", key=f"deld_{r['id']}", type="secondary"):
                        storage.delete_pdf(r["id"])
                        st.rerun()

                st.caption(
                    f"受众：{full['audience']}"
                    + (f"　|　额外要求：{full['extra_instructions']}" if full["extra_instructions"] else "")
                )
                if st.session_state.get(f"_pv_{r['id']}"):
                    try:
                        import fitz
                        pdf = fitz.open(stream=full["pdf_blob"], filetype="pdf")
                        for i, p in enumerate(pdf, start=1):
                            pix = p.get_pixmap(dpi=120)
                            st.image(pix.tobytes("png"), caption=f"第 {i} 页", use_container_width=True)
                        pdf.close()
                    except Exception as e:
                        st.warning(f"预览失败：{e}")

    st.stop()

if page == "🎁 生成引流资料 PDF":
    st.subheader("🎁 引流资料 PDF 生成器")
    st.caption("粉丝评论区扣关键词 → 你直接发这份 PDF 给他")

    magnets = data.libraries()["lead_magnet_examples"]
    options = [f"【{m['keyword']}】 {m['resource_name']}" for m in magnets]

    col_a, col_b = st.columns([3, 1])
    with col_a:
        chosen = st.selectbox("选择资料", options=range(len(options)), format_func=lambda i: options[i])
    with col_b:
        lm_audience = st.selectbox("受众", ["parent", "student", "both"],
                                   format_func=lambda x: {"parent":"家长","student":"学生","both":"都行"}[x],
                                   key="lm_audience")

    m = magnets[chosen]
    st.info(f"**关键词**：{m['keyword']}　　**资料名**：《{m['resource_name']}》　　**描述**：{m['resource_desc']}")

    custom_resource = st.text_input("✏️ 也可以自定义资料名（覆盖上方）", value="", placeholder=f"留空则使用《{m['resource_name']}》")
    custom_desc = st.text_input("✏️ 自定义描述（可选）", value="",
                                help="资料的简介，告诉 LLM 这份资料是讲什么的（影响整体方向）")
    extra_instructions = st.text_area(
        "🎯 额外要求（可选，强烈影响内容和风格）",
        value="",
        placeholder="例如：\n- 章节数 6 个，每章必须包含初一到初三的对应内容\n- 例题难度从易到难递进，第 1 章用简单题、最后一章用压轴题\n- 风格更严肃专业一点，少用'我'\n- 重点突出深圳南山区/福田区的校情差异\n- 在引言加入 2024 年中考真实数据",
        height=120,
        help="这里写的内容会作为强约束注入 prompt，可控制章节数量、难度、风格、侧重点等",
    )

    gen_pdf = st.button("📄 生成 PDF", type="primary")

    if gen_pdf:
        if not api_key:
            st.error("⚠️ 请先在左侧填入千问 API Key")
        else:
            keyword = m["keyword"]
            resource_name = custom_resource.strip() or m["resource_name"]
            resource_desc = custom_desc.strip() or m["resource_desc"]

            with st.spinner("⏳ 千问生成内容中..."):
                try:
                    content = lead_magnet_gen.generate_content(
                        keyword=keyword,
                        resource_name=resource_name,
                        resource_desc=resource_desc,
                        audience=lm_audience,
                        extra_instructions=extra_instructions.strip(),
                    )
                except llm_client.LLMError as e:
                    st.error(f"❌ {e}")
                    st.stop()

            st.success(f"✅ 内容生成完成：《{content.get('title','')}》— {len(content.get('sections',[]))} 个章节")

            with st.spinner("🎨 渲染 PDF..."):
                pdf_bytes = lead_magnet_gen.render_pdf(content)

            # 自动存档
            try:
                pid = storage.save_pdf(
                    keyword=keyword,
                    resource_name=resource_name,
                    audience=lm_audience,
                    extra_instructions=extra_instructions.strip(),
                    content=content,
                    pdf_bytes=pdf_bytes,
                )
                st.toast(f"📚 已存入历史记录 #{pid:04d}", icon="✅")
            except Exception as e:
                st.warning(f"存档失败（不影响下载）：{e}")

            st.session_state["last_pdf"] = pdf_bytes
            st.session_state["last_pdf_name"] = f"{resource_name}.pdf"
            st.session_state["last_pdf_content"] = content

    if "last_pdf" in st.session_state:
        st.divider()
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                "📥 下载 PDF",
                data=st.session_state["last_pdf"],
                file_name=st.session_state["last_pdf_name"],
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
            st.caption(f"大小：{len(st.session_state['last_pdf'])//1024} KB")
        with col2:
            st.write(f"**📄 {st.session_state['last_pdf_name']}**")
            st.caption("下载后可直接发送给小红书私信粉丝")

        with st.expander("👀 预览 PDF（图片）", expanded=True):
            try:
                import fitz  # PyMuPDF
                pdf = fitz.open(stream=st.session_state["last_pdf"], filetype="pdf")
                st.caption(f"共 {pdf.page_count} 页")
                for i, page in enumerate(pdf, start=1):
                    pix = page.get_pixmap(dpi=150)
                    st.image(pix.tobytes("png"), caption=f"第 {i} 页", use_container_width=True)
                pdf.close()
            except Exception as e:
                st.warning(f"图片预览失败：{e}")
                st.json(st.session_state["last_pdf_content"])

        with st.expander("🔧 查看 JSON 结构（调试用）"):
            st.json(st.session_state["last_pdf_content"])

    st.stop()  # 不再渲染下面的"生成帖子"页

# Input row
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    topic = st.text_input("🎯 帖子主题", placeholder="如：二次函数最值 / 错题本 / 深圳中考 / 孩子假装努力")
with col2:
    audience = st.selectbox("👥 受众", ["parent", "student", "both"], format_func=lambda x: {"parent":"家长","student":"学生","both":"都行"}[x])
with col3:
    extra_notes = ""
    st.write("")
    st.write("")

# Recommendation preview
if topic:
    rec = recommender.recommend(topic, audience)
    template_options = [r["template_id"] for r in rec["templates"]]
    default_idx = 0

    free_mode = st.checkbox(
        "🤖 自由模式（不限定模板，让 AI 根据主题 + 额外要求自由设计结构）",
        value=False,
        help="勾选后跳过模板选择，AI 自由组合 block。适合主题特殊、不想被模板束缚时使用。",
    )

    if not free_mode:
        template_id = st.selectbox(
            "📊 模板（已按主题推荐排序）",
            options=template_options + [t["id"] for t in data.templates() if t["id"] not in template_options],
            index=default_idx,
            format_func=lambda x: f"{x} · {data.get_template(x)['name']}",
        )

        with st.expander("🔍 查看推荐详情"):
            for r in rec["templates"]:
                st.write(f"- **{r['template_id']}** 分数 {r['score']} · 命中范例 {r['matched_posts']}")
            st.write("**few-shot 范例帖**：")
            for p in rec["few_shot_posts"][:3]:
                st.write(f"  - {p['id']} {p['title']}（{p['template_id']}）")
    else:
        template_id = None
        st.info("💡 自由模式：AI 会参考 few-shot 范例的语感，但 block 结构完全自由。**额外要求**这时变得很关键。")

    extra_notes = st.text_area(
        "✍️ 额外要求（可选）",
        placeholder="如：必须包含 2024 深圳中考真题；语气更扎心一点；不要用'家长'称呼，用'你'",
        height=80,
    )

    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
        generate_btn = st.button("🚀 生成帖子", type="primary", use_container_width=True)
    with btn_col2:
        dry_run = st.checkbox("Dry run（只看 prompt，不调 LLM）", value=False)

    if generate_btn:
        if not api_key and not dry_run:
            st.error("⚠️ 请先在左侧填入千问 API Key，或勾选 Dry run")
        else:
            system_prompt, user_prompt = prompt_builder.build_prompt(
                topic=topic,
                audience=audience,
                template_id=template_id,
                few_shot_posts=rec["few_shot_posts"],
                extra_notes=extra_notes or None,
            )

            if dry_run:
                st.subheader("🔧 SYSTEM PROMPT")
                st.code(system_prompt, language="text")
                st.subheader("🔧 USER PROMPT")
                st.code(user_prompt, language="text")
            else:
                with st.spinner("⏳ 千问生成中..."):
                    try:
                        result = llm_client.generate_blocks(system_prompt, user_prompt)
                        st.session_state["last_result"] = result
                        st.session_state["last_topic"] = topic
                        # 自动存档（先渲染 body 再存）
                        try:
                            _body = renderer.render(result["blocks"])
                            pid = storage.save_post(
                                topic=topic,
                                audience=audience,
                                mode="free" if free_mode else "template",
                                template_id=template_id,
                                extra_notes=extra_notes,
                                body_text=_body,
                                blocks=result["blocks"],
                            )
                            st.toast(f"📚 已存入历史记录 #{pid:04d}", icon="✅")
                        except Exception as _e:
                            st.warning(f"存档失败（不影响显示）：{_e}")
                    except llm_client.LLMError as e:
                        st.error(f"❌ {e}")
                        st.stop()

# ---------- Result Display ----------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    blocks = result["blocks"]

    st.divider()
    st.header("📝 生成结果")

    tab1, tab2, tab3 = st.tabs(["🎨 渲染预览", "🧩 Block 列表", "🔧 原始 JSON"])

    with tab1:
        body = renderer.render(blocks)
        st.text_area(
            "👇 直接复制以下内容到小红书",
            value=body,
            height=600,
            help="点击右上角的复制按钮",
        )

        # 一键复制 + 跳转小红书
        import json as _json
        import streamlit.components.v1 as components
        body_js = _json.dumps(body)  # 安全转义为 JS 字符串
        components.html(f"""
        <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;">
          <button id="cpBtn" style="
            background:#FF2442;color:white;border:none;border-radius:8px;
            padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;
            box-shadow:0 2px 6px rgba(255,36,66,.3);">
            📋 一键复制并跳转小红书发布页
          </button>
          <button id="cpOnly" style="
            background:white;color:#FF2442;border:1.5px solid #FF2442;border-radius:8px;
            padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;">
            📋 仅复制
          </button>
          <span id="tip" style="align-self:center;color:#666;font-size:13px;"></span>
        </div>
        <script>
          const text = {body_js};
          const tip = document.getElementById('tip');
          async function copyText() {{
            try {{
              await navigator.clipboard.writeText(text);
              return true;
            }} catch (e) {{
              const ta = document.createElement('textarea');
              ta.value = text; document.body.appendChild(ta);
              ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
              return true;
            }}
          }}
          document.getElementById('cpBtn').onclick = async () => {{
            const ok = await copyText();
            tip.textContent = ok ? '✅ 已复制，正在打开小红书发布页…' : '❌ 复制失败';
            tip.style.color = ok ? '#0a8' : '#c00';
            if (ok) {{
              setTimeout(() => {{
                window.open('https://creator.xiaohongshu.com/publish/publish?source=official', '_blank');
              }}, 400);
            }}
          }};
          document.getElementById('cpOnly').onclick = async () => {{
            const ok = await copyText();
            tip.textContent = ok ? '✅ 已复制到剪贴板' : '❌ 复制失败';
            tip.style.color = ok ? '#0a8' : '#c00';
          }};
        </script>
        """, height=70)
        st.caption("💡 跳转的是小红书创作者中心网页发布页，登录后 Ctrl+V 粘贴正文即可。手机端建议直接复制后切到 App。")

        if st.button("🏷️ 生成 5 个备选标题"):
            with st.spinner("⏳ 生成标题..."):
                try:
                    titles = llm_client.generate_titles(body)
                    st.subheader("备选标题")
                    for t in titles:
                        st.write(f"**[{t.get('style','')}]** {t.get('text','')}")
                except Exception as e:
                    st.error(f"标题生成失败：{e}")

    with tab2:
        st.caption("每个 block 可以单独编辑（v2 会支持单独重新生成）")
        for i, b in enumerate(blocks):
            with st.expander(f"Block {i+1}: `{b.get('type')}`", expanded=False):
                st.json(b)

    with tab3:
        st.json(result)
        st.download_button(
            "📥 下载 JSON",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name=f"{st.session_state.get('last_topic','post')}.json",
            mime="application/json",
        )

else:
    if not topic:
        st.info("👆 在上方输入帖子主题开始")
