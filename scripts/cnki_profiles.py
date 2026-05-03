#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TOP_INSTITUTIONS = {
    "清华大学", "北京大学", "浙江大学", "上海交通大学", "哈尔滨工业大学", "西安交通大学",
    "中国科学技术大学", "南京大学", "复旦大学", "同济大学", "东南大学", "华中科技大学",
    "武汉大学", "中山大学", "北京航空航天大学", "北京理工大学", "电子科技大学", "西北工业大学",
    "大连理工大学", "天津大学", "山东大学", "湖南大学", "中南大学", "重庆大学", "四川大学",
    "中国农业大学", "华南理工大学", "厦门大学", "吉林大学", "东北大学", "兰州大学",
    "中国科学院大学", "南方科技大学", "西湖大学",
}

STRONG_ENGINEERING_UNIVERSITIES = {
    "北京交通大学", "北京科技大学", "南京理工大学", "南京航空航天大学", "合肥工业大学",
    "中国矿业大学", "中国地质大学", "武汉理工大学", "西南交通大学", "河海大学",
    "江南大学", "哈尔滨工程大学", "北京工业大学", "上海大学", "苏州大学", "郑州大学",
    "福州大学", "太原理工大学", "燕山大学", "昆明理工大学", "长沙理工大学",
}

JOURNAL_KEYWORDS = (
    "学报", "自动化", "机器人", "仪器仪表", "测绘", "控制", "导航",
    "雷达", "激光", "电子学报", "机械", "机电", "传感器",
)

COMMON_DOWNRANK_TERMS = (
    "教学改革", "课程设计", "科普", "企业介绍", "产品介绍", "市场分析",
)

COMMON_EXCLUDE_TERMS = (
    "征稿", "会议通知", "新闻", "访谈", "报道", "招生", "简讯",
)

PROFILE_DEFAULTS = {
    "generic-cn-academic": {
        "rate_limit_per_minute": 10,
        "score_weights": {
            "relevance": 40,
            "source_quality": 20,
            "recency": 10,
            "citations": 15,
            "downloads": 10,
            "discipline_fit": 5,
        },
        "priority_terms": (),
        "downrank_terms": COMMON_DOWNRANK_TERMS,
        "exclude_terms": COMMON_EXCLUDE_TERMS,
        "min_year": 2010,
        "preferred_recent_years": 5,
        "output_root": PROJECT_ROOT / "output",
        "reference_profile": "generic-cn-academic",
    },
    "gbt7714-thesis-numeric": {
        "rate_limit_per_minute": 10,
        "score_weights": {
            "relevance": 42,
            "source_quality": 18,
            "recency": 10,
            "citations": 15,
            "downloads": 10,
            "discipline_fit": 5,
        },
        "priority_terms": (),
        "downrank_terms": COMMON_DOWNRANK_TERMS,
        "exclude_terms": COMMON_EXCLUDE_TERMS,
        "min_year": 2010,
        "preferred_recent_years": 5,
        "output_root": PROJECT_ROOT / "output",
        "reference_profile": "gbt7714-thesis-numeric",
    },
}


def get_profile(name: str) -> dict:
    if name not in PROFILE_DEFAULTS:
        raise KeyError(f"unknown profile: {name}")
    profile = dict(PROFILE_DEFAULTS[name])
    profile["score_weights"] = dict(PROFILE_DEFAULTS[name]["score_weights"])
    profile["priority_terms"] = list(PROFILE_DEFAULTS[name]["priority_terms"])
    profile["downrank_terms"] = list(PROFILE_DEFAULTS[name]["downrank_terms"])
    profile["exclude_terms"] = list(PROFILE_DEFAULTS[name]["exclude_terms"])
    return profile


def split_cli_terms(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for value in values:
        for part in re.split(r"[,\n;；、]+", value):
            part = part.strip()
            if part:
                out.append(part)
    return out


def topic_terms(topic: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"[\s,;；、/|]+", topic or "") if item.strip()]
    return [part for part in parts if len(part) >= 2]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def make_citation_key(title: str, year: str = "") -> str:
    normalized = normalize_text(title)
    ascii_title = re.sub(r"[^A-Za-z0-9]+", "", normalized).lower()
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in normalized)
    if ascii_title and (not has_cjk or len(ascii_title) >= 12):
        base = ascii_title[:24]
    else:
        digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8]
        base = f"cnki{digest}"
    year_digits = re.search(r"(19|20)\d{2}", year or "")
    if year_digits:
        return f"{base}{year_digits.group(0)}"
    return base


def infer_category(row: dict) -> str:
    text = " ".join(str(row.get(key, "")) for key in ("type", "source", "institution"))
    if any(token in text for token in ("硕士", "博士", "学位", "[D]")):
        return "degree"
    return "journal"
