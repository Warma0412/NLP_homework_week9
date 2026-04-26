# 🧠 信息抽取与知识图谱构建系统 (Week 8 · Vibe 实验)

基于 **Streamlit + pyvis (vis-network)** 的单页交互式 Web 应用，实现:

1. 命名实体识别 (NER) + BIO 标注切换
2. 实体关系抽取 (Subject / Predicate / Object 表格)
3. 知识图谱交互可视化 (拖拽、缩放、悬浮)

> 抽取引擎为内置的词典 / 规则版 Mock，零外部依赖即可跑通；实际教学中可替换为 spaCy 或大模型 API。

## 目录结构

```
streamlit_ie_app/
├── app.py            # Streamlit 主程序（单页）
├── extractor.py      # NER + BIO + 关系抽取 (Mock)
├── graph_viz.py      # pyvis / vis-network 图谱可视化
├── requirements.txt  # 依赖
└── README.md
```

## 本地运行

```bash
cd streamlit_ie_app
pip install -r requirements.txt
streamlit run app.py
```

启动后浏览器访问 http://localhost:8501。

## 部署到 Streamlit Cloud

1. 把整个 `streamlit_ie_app/` 文件夹推送到 GitHub 仓库。
2. 登录 [share.streamlit.io](https://share.streamlit.io) → **New app**。
3. 选择仓库、分支，**Main file path** 填 `streamlit_ie_app/app.py`（或仓库根目录下的 `app.py`）。
4. 点击 Deploy，等待依赖安装完成即可访问公网地址。

> `requirements.txt` 已声明 `streamlit`、`pyvis`、`pandas`，Streamlit Cloud 会自动安装。

## 替换为真实抽取器

打开 `extractor.py`，把顶层 `extract(text)` 替换为调用：

```python
# spaCy 示例
import spacy
_nlp = spacy.load("en_core_web_sm")

def extract(text):
    doc = _nlp(text)
    entities = [{"start": ent.start_char, "end": ent.end_char,
                 "text": ent.text, "type": ent.label_} for ent in doc.ents]
    bio = bio_tagging(text, entities)          # 复用已实现的 BIO
    relations = []                             # 可接入 REBEL / LLM
    return {"entities": entities, "bio": bio, "relations": relations}
```

或者把 `extract` 改为调用 LLM（OpenAI / 豆包 / Claude API），让模型以 JSON 形式返回 `entities` 与 `relations`，UI 层无需任何改动。
