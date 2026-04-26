"""
Week 8 Vibe 实验 —— 信息抽取与知识图谱构建系统
=====================================================
单页 Streamlit 应用。按顺序展示三个模块:
  模块 1: 命名实体识别 + BIO 标注
  模块 2: 实体关系抽取
  模块 3: 知识图谱交互可视化

运行:
    pip install -r requirements.txt
    streamlit run app.py
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from extractor import (
    ENTITY_COLORS,
    ENTITY_LABELS,
    extract,
)
from graph_viz import build_graph_html


# ---------------------------------------------------------------------------
# 页面基础配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="信息抽取与知识图谱构建系统",
    page_icon="🧠",
    layout="wide",
)

DEFAULT_TEXT = (
    "Steve Jobs and Steve Wozniak founded Apple in Cupertino, California. "
    "Tim Cook is the CEO of Apple. "
    "Apple is headquartered in Cupertino. "
    "Elon Musk founded SpaceX and works at Tesla. "
    "Jeff Bezos founded Amazon in Seattle. "
    "张一鸣创立了字节跳动,字节跳动总部位于北京。"
)


# ---------------------------------------------------------------------------
# 顶部标题
# ---------------------------------------------------------------------------
st.title("🧠 信息抽取与知识图谱构建系统")
st.caption(
    "Week 8 · Vibe Coding 实验：命名实体识别 (NER) · 关系抽取 (RE) · 知识图谱 (KG) 可视化"
)

with st.expander("📘 实验说明 (点击展开)", expanded=False):
    st.markdown(
        """
        - **模块 1** — 命名实体识别：在多行文本中高亮实体，并可切换到底层 **BIO 序列** 展示。
        - **模块 2** — 关系抽取：在实体之间预测语义关系 (Subject, Predicate, Object)。
        - **模块 3** — 知识图谱：把 "线性文本" 转换成 "网状结构数据",支持拖拽、缩放与节点悬浮查看。

        > 当前抽取引擎为内置的 **规则 / 词典** Mock 版，用于教学演示。
        > 进阶时可在 `extractor.py` 中替换为 spaCy 或大模型 API。
        """
    )


# ---------------------------------------------------------------------------
# 侧边栏 —— 输入 & 控制
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 控制面板")

    show_bio = st.checkbox("🔬 查看底层 BIO 标注", value=False)
    show_evidence = st.checkbox("📎 在关系表中展示证据句", value=True)

    st.divider()
    st.subheader("🎨 实体类别图例")
    for etype, color in ENTITY_COLORS.items():
        st.markdown(
            f"<span style='display:inline-block;width:14px;height:14px;"
            f"background:{color};border-radius:3px;margin-right:8px;"
            f"vertical-align:middle;'></span>"
            f"<b>{etype}</b> — {ENTITY_LABELS.get(etype, etype)}",
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(
        "💡 小贴士：尝试嵌套实体，如 `University of California, Los Angeles`，"
        "观察单层 BIO 的局限性。"
    )


# ---------------------------------------------------------------------------
# 文本输入区
# ---------------------------------------------------------------------------
st.subheader("✍️ 输入文本")
text_input = st.text_area(
    label="请粘贴一段英文或中文语料：",
    value=DEFAULT_TEXT,
    height=160,
    label_visibility="collapsed",
)

run = st.button("🚀 开始抽取", type="primary", use_container_width=True)

# 首次加载或点击后都会运行；这样可以直接看到默认样例效果
if not text_input.strip():
    st.warning("请先输入一些文本。")
    st.stop()

result: Dict = extract(text_input)
entities: List[Dict] = result["entities"]
bio: List[Dict] = result["bio"]
relations: List[Dict] = result["relations"]


# ---------------------------------------------------------------------------
# 模块 1 —— NER + BIO
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("🛠️ 模块 1 · 命名实体识别 & BIO 标注")

col1, col2, col3 = st.columns(3)
col1.metric("识别实体数", len(entities))
col2.metric("唯一实体数", len({e["text"] for e in entities}))
col3.metric("涉及类别数", len({e["type"] for e in entities}))


def render_highlight(text: str, ents: List[Dict]) -> str:
    """把原文按实体区间拆分，实体区间用彩色 span 包裹。"""
    if not ents:
        return f"<div style='line-height:2;font-size:16px;'>{_html.escape(text)}</div>"

    ents_sorted = sorted(ents, key=lambda x: x["start"])
    pieces = []
    cur = 0
    for ent in ents_sorted:
        if ent["start"] > cur:
            pieces.append(_html.escape(text[cur:ent["start"]]))
        color = ENTITY_COLORS.get(ent["type"], "#DDDDDD")
        label = ENTITY_LABELS.get(ent["type"], ent["type"])
        pieces.append(
            f"<span style='background:{color};padding:2px 6px;border-radius:4px;"
            f"margin:0 2px;font-weight:600;' title='{label}'>"
            f"{_html.escape(ent['text'])}"
            f"<sub style='font-size:10px;color:#333;margin-left:4px;'>"
            f"{ent['type']}</sub>"
            f"</span>"
        )
        cur = ent["end"]
    if cur < len(text):
        pieces.append(_html.escape(text[cur:]))
    return (
        "<div style='line-height:2;font-size:16px;white-space:pre-wrap;"
        "background:#fafafa;padding:16px;border-radius:8px;border:1px solid #eee;'>"
        + "".join(pieces)
        + "</div>"
    )


def render_bio(bio_seq: List[Dict]) -> str:
    """以带色块的 token/tag 并列形式展示 BIO 序列。"""
    chips = []
    for item in bio_seq:
        tag = item["tag"]
        tok = item["token"]
        if tag == "O":
            bg = "#f0f0f0"
            color_bar = "#bbbbbb"
        else:
            etype = tag.split("-", 1)[1]
            bg = ENTITY_COLORS.get(etype, "#DDDDDD")
            color_bar = "#555555"
        chips.append(
            f"<div style='display:inline-flex;flex-direction:column;align-items:center;"
            f"margin:4px 4px;padding:4px 8px;background:{bg};border-radius:6px;"
            f"min-width:36px;border:1px solid {color_bar};'>"
            f"<span style='font-family:ui-monospace,monospace;font-size:14px;'>"
            f"{_html.escape(tok)}</span>"
            f"<span style='font-size:11px;color:#333;margin-top:2px;'>{tag}</span>"
            f"</div>"
        )
    return (
        "<div style='background:#fafafa;padding:12px;border-radius:8px;"
        "border:1px solid #eee;'>" + "".join(chips) + "</div>"
    )


if show_bio:
    st.markdown("**🔬 底层 BIO 标注序列**")
    st.markdown(render_bio(bio), unsafe_allow_html=True)
    st.caption(
        "B- = Begin (实体起始 token) · I- = Inside (实体内部 token) · O = Outside (非实体)"
    )
else:
    st.markdown("**🎯 实体高亮视图**")
    st.markdown(render_highlight(text_input, entities), unsafe_allow_html=True)

with st.expander("📋 实体明细表"):
    if entities:
        df_ent = pd.DataFrame(entities)
        df_ent["类别"] = df_ent["type"].map(lambda t: f"{t} — {ENTITY_LABELS.get(t, t)}")
        df_ent = df_ent[["text", "类别", "start", "end"]].rename(
            columns={"text": "实体文本", "start": "起始", "end": "结束"}
        )
        st.dataframe(df_ent, use_container_width=True, hide_index=True)
    else:
        st.info("未识别到实体。")


# ---------------------------------------------------------------------------
# 模块 2 —— 关系抽取
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("🛠️ 模块 2 · 实体关系抽取")

if relations:
    rows = []
    for r in relations:
        row = {
            "主体 (Subject)": r["source"],
            "关系 (Predicate)": r["relation"],
            "客体 (Object)": r["target"],
        }
        if show_evidence:
            row["证据句 (Evidence)"] = r.get("evidence", "")
        rows.append(row)
    df_rel = pd.DataFrame(rows)
    st.dataframe(df_rel, use_container_width=True, hide_index=True)
    st.caption(
        f"共抽取到 **{len(relations)}** 条关系三元组。"
        f"关系抽取本质是在图结构中为两个实体节点之间预测是否存在特定语义类型的边。"
    )
else:
    st.info("未抽取到关系。尝试加入更明确的谓词，如 `founded` / `is the CEO of` / `总部位于` 等。")


# ---------------------------------------------------------------------------
# 模块 3 —— 知识图谱
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("🛠️ 模块 3 · 知识图谱交互可视化")

if entities and relations:
    graph_html = build_graph_html(entities, relations)
    components.html(graph_html, height=620, scrolling=True)
    st.caption(
        "支持 🖱️ 拖拽节点、滚轮缩放、悬浮查看。"
        "不同颜色代表不同实体类别,箭头方向为 Subject → Object,边上标签为关系类型。"
    )
elif entities and not relations:
    st.warning("只抽取到实体、没有抽取到关系,无法构建关系图。")
else:
    st.info("尚未抽取到任何实体。")


# ---------------------------------------------------------------------------
# 底部观察任务
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("👀 观察 & 思考")
st.markdown(
    """
    1. 在模块 1 中切换 **"查看底层 BIO 标注"**,对比 UI 高亮 vs BIO 序列,
       体会 **B (Begin) / I (Inside) / O (Outside)** 如何决定实体边界。
    2. 输入 `University of California, Los Angeles`,观察嵌套实体
       (`Los Angeles` 本身也是地名) 在单层 BIO 下的局限。
    3. 在模块 2 中输入带有代词 (如 *"He founded ..."*) 的句子,
       思考关系抽取对 **指代消解** 的依赖。
    4. 在模块 3 中,观察一段包含多人物 / 多机构的新闻如何被转化为
       **网状知识结构**——这正是知识图谱的构建起点。
    """
)
