"""
知识图谱可视化工具
---------------------------
使用 pyvis 生成交互式 HTML 网络图 (基于 vis-network.js)，
再通过 Streamlit 的 components.html 嵌入页面。
"""
from __future__ import annotations

from typing import Dict, List

from pyvis.network import Network

from extractor import ENTITY_COLORS, ENTITY_LABELS


def build_graph_html(entities: List[Dict], relations: List[Dict]) -> str:
    net = Network(
        height="600px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
    )
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=160,
        spring_strength=0.04,
        damping=0.9,
    )

    # 节点: 按实体 text 去重
    added = {}
    for ent in entities:
        key = ent["text"]
        if key in added:
            continue
        color = ENTITY_COLORS.get(ent["type"], "#DDDDDD")
        label_type = ENTITY_LABELS.get(ent["type"], ent["type"])
        net.add_node(
            key,
            label=key,
            title=f"{label_type} ({ent['type']})",
            color=color,
            shape="dot",
            size=28,
        )
        added[key] = True

    # 如果关系中的端点没有出现在实体列表(极少数情况)，补一个 MISC 节点
    for rel in relations:
        for endpoint in (rel["source"], rel["target"]):
            if endpoint not in added:
                net.add_node(
                    endpoint,
                    label=endpoint,
                    color=ENTITY_COLORS["MISC"],
                    shape="dot",
                    size=24,
                )
                added[endpoint] = True

    for rel in relations:
        net.add_edge(
            rel["source"],
            rel["target"],
            label=rel["relation"],
            title=rel.get("evidence", ""),
            arrows="to",
            color={"color": "#888888"},
            font={"size": 12, "align": "middle"},
        )

    # 额外的 vis-network 选项 (JSON 字符串)
    net.set_options("""
    {
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "zoomView": true,
        "dragNodes": true
      },
      "edges": {
        "smooth": {"type": "dynamic"}
      },
      "physics": {
        "stabilization": {"iterations": 150}
      }
    }
    """)

    return net.generate_html(notebook=False)
