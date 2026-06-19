# src/special_categories.py
"""智能补充 - 从 abc123 源采集频道，只追加新分类到末尾"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from src.logger import logger
from src.classifier import PROVINCES

# 新分类关键词（清晰细分）
NEW_CATEGORY_KEYWORDS = {
    "🎬 电影频道": ["电影", "影院", "影片", "CHC", "动作电影", "家庭影院", "影迷电影", "经典电影", "华语影院", "峨眉电影", "新片放映厅", "抗战经典影片", "经典香港电影"],
    "📺 电视剧频道": ["电视剧", "剧场", "热播", "TVB", "港剧", "韩剧", "美剧", "日剧", "穿越剧"],
    "🎬 动漫频道": ["动漫", "动画", "卡通", "新动漫", "爱动漫", "动漫秀场"],
    "🎬 综艺频道": ["综艺", "娱乐", "明星", "选秀", "脱口秀", "搞笑"],
    "🎤 音乐频道": ["音乐", "歌曲", "老歌", "金曲", "流行", "经典老歌", "香香音乐", "DJ", "舞曲", "动感", "节奏", "音悦", "经典歌曲"],
    "🎭 戏曲频道": ["戏曲", "京剧", "越剧", "黄梅戏", "豫剧", "评剧", "秦腔", "昆曲", "粤剧", "河北梆子", "梨园", "梨园春", "移动戏曲", "岭南戏曲"],
    "🏀 体育频道": ["体育", "NBA", "CBA", "世界杯", "英超", "西甲", "德甲", "意甲", "法甲", "中超", "欧冠", "亚冠", "斯诺克", "WTA", "WTT", "BWF", "UFC", "赛车", "F1", "电竞", "五星体育"],
    "👶 少儿频道": ["少儿", "儿童", "卡通", "动画", "金鹰卡通", "嘉佳卡通", "卡酷", "炫动卡通", "优漫卡通"],
    "💰 财经频道": ["财经", "经济", "财富", "金融", "股票", "投资"],
    "📻 网络电台": ["电台", "广播", "FM", "AM", "网络电台", "音频", "听书", "有声", "音乐广播", "交通广播", "新闻广播"],
    "🌍 国际频道": ["国际", "海外", "美洲", "欧洲", "亚洲", "环球", "CGTN"],
}

EXCLUDE_KEYWORDS = ["广场舞", "健身", "教学", "讲座", "访谈", "天气预报", "直播", "回放", "全场", "解说", "原声", "字幕", "回看"]


def get_province_from_name(name: str) -> Optional[str]:
    for prov in PROVINCES:
        if prov in name:
            return prov
    alias = {"京": "北京", "沪": "上海", "津": "天津", "渝": "重庆"}
    for short, full in alias.items():
        if short in name:
            return full
    return None


def classify_channel_to_demo(name: str, demo_categories: set) -> Optional[str]:
    """返回匹配的 demo 分类名，或 None"""
    name_lower = name.lower()
    
    # 央视
    if re.search(r'(cctv|央视|中央台)', name_lower):
        for cat in demo_categories:
            if '央视' in cat:
                return cat
        return None
    
    # 省份地方频道
    province = get_province_from_name(name)
    if province:
        # 查找 demo 中对应的省份分类
        candidates = [f"☘️{province}频道", f"{province}频道", f"☘️{province}", province]
        for cat in demo_categories:
            for cand in candidates:
                if cand in cat or cat in cand:
                    return cat
        return None  # 不在 demo 中，不追加（避免创建多余分类）
    
    # 卫视
    if '卫视' in name:
        for cat in demo_categories:
            if '卫视' in cat:
                return cat
        return None
    
    # 港澳台
    hmtj = ["香港", "澳门", "台湾", "港", "澳", "台"]
    if any(kw in name for kw in hmtj):
        for cat in demo_categories:
            if '港澳台' in cat or '港·澳·台' in cat:
                return cat
        return None
    
    return None


def classify_new_category(name: str) -> Optional[str]:
    name_lower = name.lower()
    for exclude in EXCLUDE_KEYWORDS:
        if exclude.lower() in name_lower:
            return None
    for category, keywords in NEW_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return "🎬 综合频道"  # 兜底


async def fetch_and_classify_special_sources(db=None, demo_order: List[Tuple[str, str]] = None) -> Dict[str, List[Tuple[str, str]]]:
    source_url = "https://tv.19860519.xyz/abc123"
    from src.fetcher import fetch_url_with_metadata
    
    try:
        content = await fetch_url_with_metadata(source_url, db)
        if not content:
            return {}
    except Exception as e:
        logger.error(f"❌ 获取源失败: {e}")
        return {}
    
    all_channels = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.endswith(',#genre#'):
            continue
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                name, url = parts[0].strip(), parts[1].strip()
                if url.startswith(('http://', 'https://')):
                    all_channels.append((name, url))
    
    if not all_channels:
        return {}
    
    demo_categories = {cat for cat, _ in demo_order} if demo_order else set()
    result = defaultdict(list)
    
    for name, url in all_channels:
        # 先尝试匹配 demo 分类
        demo_cat = classify_channel_to_demo(name, demo_categories)
        if demo_cat:
            result[demo_cat].append((name, url))
            continue
        # 否则创建新分类
        new_cat = classify_new_category(name)
        if new_cat:
            result[new_cat].append((name, url))
    
    # 去重
    for cat in result:
        seen = set()
        unique = []
        for name, url in result[cat]:
            if url not in seen:
                seen.add(url)
                unique.append((name, url))
        result[cat] = unique
    
    # 只返回新分类（不在 demo 中的）
    final_result = {cat: channels for cat, channels in result.items() if cat not in demo_categories}
    
    if final_result:
        logger.info(f"📊 智能补充统计: 共 {sum(len(v) for v in final_result.values())} 个频道")
        for cat, channels in final_result.items():
            logger.info(f"   🆕 {cat}: {len(channels)} 个频道")
    
    return final_result


def append_special_to_output(special_data: Dict[str, List[Tuple[str, str]]], output_dir: Path) -> Dict[str, int]:
    if not special_data:
        return {}
    
    m3u_path = output_dir / "tv.m3u"
    txt_path = output_dir / "tv.txt"
    total = 0
    
    with open(m3u_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 智能补充内容 ==========\n")
        for cat, channels in special_data.items():
            if not channels:
                continue
            f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
            for name, url in channels:
                f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
                total += 1
    
    with open(txt_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 智能补充内容 ==========\n")
        for cat, channels in special_data.items():
            if not channels:
                continue
            f.write(f"\n{cat},#genre#\n")
            for name, url in channels:
                f.write(f"{name},{url}\n")
    
    logger.info(f"✅ 已将 {total} 个频道追加到输出文件（新分类: {list(special_data.keys())}）")
    return {cat: len(ch) for cat, ch in special_data.items()}
