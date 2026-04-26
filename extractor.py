"""
Mock 信息抽取模块
---------------------------
为了让同学们在不依赖外部大模型 API / spaCy 模型的情况下直接跑通 Demo，
本模块内置了一个简易的基于词典 + 规则的 NER 与关系抽取器，
覆盖英文示例 (Steve Jobs / Apple / Tim Cook ...) 与中文常见机构/人物。

实际教学中可以把 `extract` 函数替换为:
  - spaCy:  nlp = spacy.load("en_core_web_sm")
  - LLM:    调用 OpenAI / 火山 / 豆包 API 做 zero-shot 抽取
接口保持不变:
    extract(text) -> dict(entities=[...], relations=[...], bio=[...])
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# 1. 实体词典 (Mock 版本)
# ---------------------------------------------------------------------------
# 同学们可以继续往这里添加你想测试的实体。
ENTITY_DICT: Dict[str, str] = {
    # Person
    "Steve Jobs": "PER",
    "Steve Wozniak": "PER",
    "Tim Cook": "PER",
    "Bill Gates": "PER",
    "Elon Musk": "PER",
    "Jeff Bezos": "PER",
    "Mark Zuckerberg": "PER",
    "Larry Page": "PER",
    "Sergey Brin": "PER",
    "马云": "PER",
    "张一鸣": "PER",
    "李彦宏": "PER",
    "雷军": "PER",

    # Organization
    "Apple": "ORG",
    "Apple Inc.": "ORG",
    "Microsoft": "ORG",
    "Google": "ORG",
    "Amazon": "ORG",
    "Meta": "ORG",
    "Facebook": "ORG",
    "Tesla": "ORG",
    "SpaceX": "ORG",
    "ByteDance": "ORG",
    "字节跳动": "ORG",
    "阿里巴巴": "ORG",
    "百度": "ORG",
    "小米": "ORG",
    "University of California": "ORG",

    # Location
    "Cupertino": "LOC",
    "California": "LOC",
    "Los Angeles": "LOC",
    "Seattle": "LOC",
    "New York": "LOC",
    "Beijing": "LOC",
    "北京": "LOC",
    "上海": "LOC",
    "杭州": "LOC",
    "深圳": "LOC",
}

# 实体类别 -> 颜色 (用于高亮 & 图谱)
ENTITY_COLORS: Dict[str, str] = {
    "PER": "#FFD6A5",   # 橙
    "ORG": "#A0C4FF",   # 蓝
    "LOC": "#BDB2FF",   # 紫
    "MISC": "#CAFFBF",  # 绿
}

ENTITY_LABELS: Dict[str, str] = {
    "PER": "Person",
    "ORG": "Organization",
    "LOC": "Location",
    "MISC": "Misc",
}

# ---------------------------------------------------------------------------
# 2. 关系模板 (Mock 版本)
# ---------------------------------------------------------------------------
# 形如: (正则模式, subject 所在组, object 所在组, relation)
RELATION_PATTERNS: List[Tuple[str, str]] = [
    (r"(?P<s>\w[\w\s\.]+?)\s+founded\s+(?P<o>\w[\w\s\.]+)", "FOUNDER_OF"),
    (r"(?P<s>\w[\w\s\.]+?)\s+co-founded\s+(?P<o>\w[\w\s\.]+)", "CO_FOUNDER_OF"),
    (r"(?P<s>\w[\w\s\.]+?)\s+is\s+the\s+CEO\s+of\s+(?P<o>\w[\w\s\.]+)", "CEO_OF"),
    (r"(?P<s>\w[\w\s\.]+?)\s+is\s+headquartered\s+in\s+(?P<o>\w[\w\s\.]+)", "HEADQUARTERED_IN"),
    (r"(?P<s>\w[\w\s\.]+?)\s+is\s+located\s+in\s+(?P<o>\w[\w\s\.]+)", "LOCATED_IN"),
    (r"(?P<s>\w[\w\s\.]+?)\s+works\s+at\s+(?P<o>\w[\w\s\.]+)", "WORKS_AT"),
    (r"(?P<s>\w[\w\s\.]+?)\s+acquired\s+(?P<o>\w[\w\s\.]+)", "ACQUIRED"),
    # 中文
    (r"(?P<s>[\u4e00-\u9fa5\w]+?)创立了(?P<o>[\u4e00-\u9fa5\w]+)", "FOUNDER_OF"),
    (r"(?P<s>[\u4e00-\u9fa5\w]+?)创办了(?P<o>[\u4e00-\u9fa5\w]+)", "FOUNDER_OF"),
    (r"(?P<s>[\u4e00-\u9fa5\w]+?)是(?P<o>[\u4e00-\u9fa5\w]+?)的(?:CEO|首席执行官|创始人)", "CEO_OF"),
    (r"(?P<s>[\u4e00-\u9fa5\w]+?)总部位于(?P<o>[\u4e00-\u9fa5\w]+)", "HEADQUARTERED_IN"),
    (r"(?P<s>[\u4e00-\u9fa5\w]+?)收购了(?P<o>[\u4e00-\u9fa5\w]+)", "ACQUIRED"),
]


# ---------------------------------------------------------------------------
# 3. NER
# ---------------------------------------------------------------------------
def find_entities(text: str) -> List[Dict]:
    """在文本中按词典匹配实体，返回按起始位置升序的列表。

    返回的每项结构:
        {"start": int, "end": int, "text": str, "type": "PER|ORG|LOC|..."}
    若出现重叠，采用 "更长优先 + 起始更靠前" 策略，丢弃被包含的短匹配。
    """
    spans: List[Dict] = []
    for surface, etype in ENTITY_DICT.items():
        # 中文不需要 \b 边界; 英文用大小写不敏感匹配
        if re.search(r"[\u4e00-\u9fa5]", surface):
            pattern = re.escape(surface)
        else:
            pattern = r"\b" + re.escape(surface) + r"\b"
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append({
                "start": m.start(),
                "end": m.end(),
                "text": text[m.start():m.end()],
                "type": etype,
            })

    # 去重 / 处理嵌套: 按 (start asc, length desc)
    spans.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    filtered: List[Dict] = []
    last_end = -1
    for sp in spans:
        if sp["start"] >= last_end:
            filtered.append(sp)
            last_end = sp["end"]
    return filtered


# ---------------------------------------------------------------------------
# 4. BIO 标注
# ---------------------------------------------------------------------------
def _tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    """粗粒度 tokenizer，返回 [(token, start, end)]。
    - 英文: 以空白和标点切分。
    - 中文: 逐字切分 (展示 BIO 效果最清晰)。
    """
    tokens: List[Tuple[str, int, int]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if "\u4e00" <= ch <= "\u9fa5":
            tokens.append((ch, i, i + 1))
            i += 1
        elif ch.isalnum() or ch == "_":
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] in "_'-"):
                j += 1
            tokens.append((text[i:j], i, j))
            i = j
        else:  # 标点
            tokens.append((ch, i, i + 1))
            i += 1
    return tokens


def bio_tagging(text: str, entities: List[Dict]) -> List[Dict]:
    """生成 BIO 标签序列。

    输出: [{"token": str, "tag": "B-PER" | "I-PER" | "O", "start":int, "end":int}, ...]
    """
    toks = _tokenize_with_offsets(text)
    # 按 token 起点 / 终点查找是否落在实体内
    ent_sorted = sorted(entities, key=lambda x: x["start"])

    out: List[Dict] = []
    for tok, s, e in toks:
        tag = "O"
        for ent in ent_sorted:
            if s >= ent["start"] and e <= ent["end"]:
                if s == ent["start"]:
                    tag = f"B-{ent['type']}"
                else:
                    tag = f"I-{ent['type']}"
                break
        out.append({"token": tok, "tag": tag, "start": s, "end": e})
    return out


# ---------------------------------------------------------------------------
# 5. 关系抽取
# ---------------------------------------------------------------------------
def extract_relations(text: str, entities: List[Dict]) -> List[Dict]:
    """基于模板正则的简易关系抽取。

    返回: [{"source":str, "target":str, "relation":str, "evidence":str}]
    仅保留 source / target 同时能在 entities 列表中（或其前缀/后缀）匹配到的关系。
    为了避免跨句子误匹配，先按句子切分，再在每个句子内独立匹配模板。
    """
    ent_surfaces = {e["text"] for e in entities}

    def _match_entities(span: str, multi: bool = False) -> List[str]:
        """在 span 中找出已知实体。
        - multi=False (默认,用于客体): 只返回 span 中最早出现的那一个实体。
        - multi=True  (用于主体): 返回 span 中所有实体,用于 "A and B founded X" 这种并列主语。
        """
        span = span.strip().strip(",.;:!?")
        if not span:
            return []
        if span in ent_surfaces:
            return [span]
        hits = []
        for s in ent_surfaces:
            idx = span.find(s)
            if idx >= 0:
                hits.append((idx, s))
        if hits:
            hits.sort()
            if multi:
                return [s for _, s in hits]
            return [hits[0][1]]
        rev = [e for e in ent_surfaces if span and span in e]
        if rev:
            return [max(rev, key=len)]
        return []

    # 句子切分 (中英文标点)
    sentences = re.split(r"(?<=[。！？\.!?])\s*", text)

    rels: List[Dict] = []
    for sent in sentences:
        if not sent.strip():
            continue
        for pattern, rel in RELATION_PATTERNS:
            for m in re.finditer(pattern, sent, flags=re.IGNORECASE):
                s_list = _match_entities(m.group("s"), multi=True)
                o_list = _match_entities(m.group("o"), multi=False)
                for s in s_list:
                    for o in o_list:
                        if s == o:
                            continue
                        rels.append({
                            "source": s,
                            "target": o,
                            "relation": rel,
                            "evidence": m.group(0).strip(),
                        })

    # 去重
    seen = set()
    uniq = []
    for r in rels:
        key = (r["source"], r["target"], r["relation"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq


# ---------------------------------------------------------------------------
# 6. 顶层接口
# ---------------------------------------------------------------------------
def extract(text: str) -> Dict:
    entities = find_entities(text)
    bio = bio_tagging(text, entities)
    relations = extract_relations(text, entities)
    return {
        "entities": entities,
        "bio": bio,
        "relations": relations,
    }
