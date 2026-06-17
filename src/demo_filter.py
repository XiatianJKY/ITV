# src/demo_filter.py
# Demo 频道筛选与排序模块，支持拼音匹配和省份自动归类

import re
from pathlib import Path
from typing import List, Tuple
from src.config import DEMO_FILE, OUTPUT_DIR, DEMO_MATCH_MODE
from src.classifier import PROVINCES, classify_channel
from src.logger import logger

# 尝试导入拼音库，若失败则回退到简单匹配
try:
    from pypinyin import lazy_pinyin, pinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    logger.warning("⚠️ pypinyin 未安装，拼音匹配功能将不可用。建议安装: pip install pypinyin")


def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    """解析 demo.txt，返回 [(分类, 频道名), ...]"""
    if not demo_file.exists():
        logger.warning(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    
    order = []
    current_category = None
    
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.endswith(",#genre#") or line.endswith(", #genre#"):
                current_category = line.replace(", #genre#", "").replace(", #genre#", "").strip()
                continue
            
            if line.startswith('#'):
                continue
            
            if current_category is not None:
                order.append((current_category, line))
            else:
                order.append(("其他", line))
    
    logger.info(f"📋 从 demo.txt 解析到 {len(order)} 个有序频道")
    return order


def to_pinyin(text: str) -> str:
    """将中文转换为拼音（小写，无空格）"""
    if not HAS_PYPINYIN:
        return text.lower()
    try:
        return ''.join(lazy_pinyin(text)).lower()
    except:
        return text.lower()


def match_channel_name(channel_name: str, demo_name: str) -> bool:
    """
    增强匹配：支持中文/拼音/子串匹配
    """
    if DEMO_MATCH_MODE == "exact":
        return channel_name == demo_name
    
    cn_lower = channel_name.lower()
    dn_lower = demo_name.lower()
    
    # 1. 直接包含匹配
    if dn_lower in cn_lower or cn_lower in dn_lower:
        return True
    
    # 2. 拼音匹配（将中文 demo 名转为拼音，检查是否在频道名中）
    if HAS_PYPINYIN:
        demo_pinyin = to_pinyin(demo_name)
        channel_pinyin = to_pinyin(channel_name)
        # 检查拼音是否包含
        if demo_pinyin in channel_pinyin or channel_pinyin in demo_pinyin:
            return True
        # 检查 demo 中文是否包含在频道名拼音中（例如 demo="浙江", 频道名="zhejiang"）
        # 也检查频道名中文是否包含 demo 拼音
        # 已经通过包含检查，但有些频道名是纯拼音，demo 是中文，需要双向检查
    
    # 3. 去除特殊字符后的匹配
    def clean(s):
        return re.sub(r'[^a-zA-Z\u4e00-\u9fa5]', '', s).lower()
    if clean(demo_name) in clean(channel_name) or clean(channel_name) in clean(demo_name):
        return True
    
    return False


def detect_province(channel_name: str) -> str:
    """
    检测频道名中的省份/城市，返回省份名（如"北京"）
    """
    name = channel_name
    # 优先匹配省份名
    for prov in PROVINCES:
        if prov in name:
            return prov
    # 匹配直辖市简称
    if "京" in name: return "北京"
    if "沪" in name: return "上海"
    if "津" in name: return "天津"
    if "渝" in name: return "重庆"
    return None


def get_demo_category_for_province(province: str, demo_order: List[Tuple[str, str]]) -> str:
    """
    根据省份名生成对应的 demo 分类名
    若 demo 中有 "☘️北京频道,#genre#" 则返回 "☘️北京频道"
    否则返回 "北京频道"
    """
    # 尝试多种格式
    candidates = [
        f"☘️{province}频道",
        f"{province}频道",
        f"☘️{province}",
        f"{province}"
    ]
    for cat, _ in demo_order:
        for cand in candidates:
            if cat.startswith(cand) or cat == cand:
                return cat
    # 若没有，返回默认格式
    return f"☘️{province}频道"


def filter_and_order_by_demo(channels: list) -> tuple:
    """
    增强筛选：
    1. 匹配 demo 中的频道（支持拼音）
    2. 未匹配的根据省份自动归类
    """
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        logger.warning("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    name_to_channel = {ch["name"]: ch for ch in channels}
    matched = []
    unmatched = list(channels)
    matched_names = set()
    
    # 第一遍：匹配 demo 中的频道名（支持拼音）
    for category, demo_name in demo_order:
        # 精确匹配
        if demo_name in name_to_channel:
            ch = name_to_channel[demo_name].copy()
            ch["demo_category"] = category
            ch["demo_name"] = demo_name
            if ch["name"] not in matched_names:
                matched.append(ch)
                matched_names.add(ch["name"])
                unmatched = [c for c in unmatched if c["name"] != ch["name"]]
                continue
        
        # 模糊/拼音匹配
        found = False
        for i, ch in enumerate(unmatched[:]):
            if ch["name"] in matched_names:
                continue
            if match_channel_name(ch["name"], demo_name):
                ch_copy = ch.copy()
                ch_copy["demo_category"] = category
                ch_copy["demo_name"] = demo_name
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                unmatched.pop(i)
                found = True
                logger.debug(f"🎯 匹配: {ch['name']} -> {category}/{demo_name}")
                break

    # 第二遍：未匹配频道自动归类到省份分类
    remaining = []
    province_appended = {}
    
    for ch in unmatched:
        # 检测省份
        province = detect_province(ch["name"])
        if province:
            # 获取对应的 demo 分类
            cat = get_demo_category_for_province(province, demo_order)
            ch_copy = ch.copy()
            ch_copy["demo_category"] = cat
            ch_copy["demo_name"] = ch["name"]
            matched.append(ch_copy)
            matched_names.add(ch["name"])
            province_appended[province] = province_appended.get(province, 0) + 1
            logger.info(f"🌏 自动归类: {ch['name']} -> {cat}")
        else:
            remaining.append(ch)
    
    if province_appended:
        logger.info(f"📊 自动归类统计: {dict(province_appended)}")
    
    logger.info(f"🎯 Demo 筛选：原始 {len(channels)} -> 匹配 {len(matched)}，未匹配 {len(remaining)}")
    return matched, remaining


def write_shai_file(unmatched_channels: list, matched_count: int, total_raw: int):
    """保存未匹配的频道列表"""
    shai_path = OUTPUT_DIR / "shai.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(shai_path, "w", encoding="utf-8") as f:
        f.write("# Demo筛选丢弃的频道\n")
        f.write(f"# 原始频道总数: {total_raw}\n")
        f.write(f"# Demo匹配成功: {matched_count}\n")
        f.write(f"# 丢弃数量: {len(unmatched_channels)}\n\n")
        
        for ch in unmatched_channels:
            url = ch["urls"][0] if ch.get("urls") else ch["url"]
            f.write(f"{ch['name']},{url}\n")
    
    logger.info(f"📄 未匹配频道列表已保存: {shai_path}")
