# src/demo_filter.py
# Demo 频道筛选与排序模块，支持地方频道和港澳台频道的自动归类

from pathlib import Path
from typing import List, Tuple
from src.config import DEMO_FILE, OUTPUT_DIR, DEMO_MATCH_MODE
from src.alias_matcher import get_alias_matcher
from src.classifier import PROVINCES, classify_channel

def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    if not demo_file.exists():
        print(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    matcher = get_alias_matcher()
    order = []
    current_category = None
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(",#genre#"):
                current_category = line[:-7]
                continue
            if line.startswith('#'):
                continue
            if current_category is not None:
                demo_name = line
                if matcher:
                    demo_name = matcher.normalize(demo_name)
                order.append((current_category, demo_name))
            else:
                order.append(("其他", line))
    print(f"📋 从 demo.txt 解析到 {len(order)} 个有序频道，共 {len(set(c for c,_ in order))} 个分类")
    return order

def match_channel_name(channel_name: str, demo_name: str) -> bool:
    if DEMO_MATCH_MODE == "exact":
        return channel_name == demo_name
    else:
        cn_lower = channel_name.lower()
        dn_lower = demo_name.lower()
        return dn_lower in cn_lower or cn_lower in dn_lower

def find_matching_demo_category(channel_name: str, demo_order: List[Tuple[str, str]]) -> str:
    for category, demo_name in demo_order:
        if match_channel_name(channel_name, demo_name):
            return category
    for prov in PROVINCES:
        if prov in channel_name:
            for category, _ in demo_order:
                if prov in category and ("频道" in category or "☘️" in category):
                    return category
    hk_tw_keywords = ["港", "澳", "台", "香港", "澳门", "台湾", "翡翠", "明珠", "凤凰", "tvb", "无线", "rthk", "hoy", "viu", "tvbs", "东森", "民视", "台视"]
    for kw in hk_tw_keywords:
        if kw.lower() in channel_name.lower():
            for category, _ in demo_order:
                if "港" in category or "澳" in category or "台" in category or "港澳台" in category:
                    return category
    return None

def filter_and_order_by_demo(channels: list) -> tuple:
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        print("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    name_to_channel = {ch["name"]: ch for ch in channels}
    matched = []
    unmatched = list(channels)
    matched_names = set()
    matched_demo_items = set()

    for category, demo_name in demo_order:
        if demo_name in name_to_channel:
            ch = name_to_channel[demo_name].copy()
            ch["demo_category"] = category
            if ch["name"] not in matched_names:
                matched.append(ch)
                matched_names.add(ch["name"])
                matched_demo_items.add(demo_name)
                unmatched = [c for c in unmatched if c["name"] != ch["name"]]
                continue
        found = False
        for i, ch in enumerate(unmatched[:]):
            if ch["name"] in matched_names:
                continue
            if match_channel_name(ch["name"], demo_name):
                ch_copy = ch.copy()
                ch_copy["demo_category"] = category
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                matched_demo_items.add(demo_name)
                unmatched.pop(i)
                found = True
                break
        if not found:
            pass

    remaining = []
    for ch in unmatched:
        cat = classify_channel(ch)
        if cat in ["地方", "港澳台"]:
            demo_cat = find_matching_demo_category(ch["name"], demo_order)
            if demo_cat:
                ch_copy = ch.copy()
                ch_copy["demo_category"] = demo_cat
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                continue
        remaining.append(ch)

    print(f"🎯 Demo 筛选：原始 {len(channels)} 个频道 -> 匹配 {len(matched)} 个频道，未匹配 {len(remaining)} 个")
    return matched, remaining

def write_shai_file(unmatched_channels: list, matched_count: int, total_raw: int):
    shai_path = OUTPUT_DIR / "shai.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(shai_path, "w", encoding="utf-8") as f:
        f.write(f"# Demo筛选丢弃的频道\n")
        f.write(f"# 原始频道总数: {total_raw}\n")
        f.write(f"# Demo匹配成功: {matched_count}\n")
        f.write(f"# 丢弃数量: {len(unmatched_channels)}\n")
        f.write(f"# 格式: 频道名,URL\n\n")
        for ch in unmatched_channels:
            url = ch["urls"][0] if ch.get("urls") else ch["url"]
            f.write(f"{ch['name']},{url}\n")
    print(f"📄 未匹配频道列表已保存到: {shai_path}")
