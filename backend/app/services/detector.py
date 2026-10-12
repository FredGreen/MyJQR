"""AI 率启发式检测（MVP 版，M3 换自训分类器微服务）。

信号：① AI 高频词/连接词密度 ② 句长方差（人写波动大）③ 段落长度方差 ④ 破折号/省略号等人工痕迹
输出 0-100（越低越像人写），口径对齐朱雀：<50 human, 50-99 suspect, >=99 ai。
"""
import re
import statistics

AI_WORDS = [
    "首先", "其次", "再次", "最后", "总而言之", "综上所述", "总的来说", "值得一提的是",
    "不得不说", "毫无疑问", "众所周知", "赋能", "抓手", "闭环", "底层逻辑", "顶层设计",
    "深度剖析", "全方位", "一站式", "新引擎", "新动能", "着力", "旨在", "日益", "愈发",
    "随着.*的发展", "在当今.*背景下", "不仅.*更是", "让我们", "Unveil", "delve",
]
CONNECTIVES = ["然而", "因此", "所以", "并且", "此外", "同时", "与此同时", "除此之外"]

HUMAN_MARKS = ["——", "……", "～", "！", "？", "吧", "呗", "嘛", "哈", "呢"]


def detect_ai_rate(text: str) -> dict:
    if not text or len(text) < 50:
        return {"ai_rate": 0, "level": "human", "detail": {"reason": "text too short"}}

    n = max(len(text), 1)
    ai_hits = sum(len(re.findall(w, text)) for w in AI_WORDS)
    conn_hits = sum(text.count(c) for c in CONNECTIVES)
    human_hits = sum(text.count(m) for m in HUMAN_MARKS)

    sentences = [s for s in re.split(r"[。！？!?\n]+", text) if len(s.strip()) >= 4]
    sent_lens = [len(s) for s in sentences] or [n]
    len_var = statistics.pstdev(sent_lens) / (statistics.mean(sent_lens) + 1e-6)  # 变异系数

    paragraphs = [p for p in text.split("\n") if len(p.strip()) >= 20]
    para_var = (statistics.pstdev([len(p) for p in paragraphs]) /
                (statistics.mean([len(p) for p in paragraphs]) + 1e-6)) if len(paragraphs) >= 3 else 0.5

    # 加权合成 0-100
    score = 30
    score += min(35, ai_hits * 800 / n * 10)          # AI 词密度
    score += min(15, conn_hits * 400 / n * 10)         # 连接词密度
    score -= min(15, human_hits * 300 / n * 10)        # 人工痕迹减分
    score -= min(10, max(0.0, len_var - 0.4) * 20)     # 句长波动大 → 更像人
    score -= min(10, max(0.0, para_var - 0.4) * 15)    # 段落波动
    score -= 10 if re.search(r"[0-9]+条|第一[，,]|第二[，,]|第三[，,]", text) is None else 0

    ai_rate = int(max(0, min(100, score)))
    level = "human" if ai_rate < 50 else ("suspect" if ai_rate < 99 else "ai")
    risky = sorted(sentences, key=lambda s: -sum(len(re.findall(w, s)) for w in AI_WORDS))[:5]
    return {"ai_rate": ai_rate, "level": level,
            "detail": {"signals": {"ai_word_hits": ai_hits, "connective_hits": conn_hits,
                                   "human_marks": human_hits, "sent_len_cv": round(len_var, 3)},
                       "risky_sentences": [s[:80] for s in risky if s]}}
