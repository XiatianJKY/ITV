# src/hmtj_source.py
"""处理 http://1080p.19860519.de5.net/ 源的采集与分类（JSON API 版）
   采集到的央视、卫视、地方、体育赛事频道直接存入稳定源（标记为固定源）
"""

import aiohttp
import json
from typing import List, Dict, Optional
from src.logger import logger


CATEGORY_MAP = {
    "group_央视": "央视",
    "group_卫视": "卫视",
    "group_地方": "地方",
}

SPORTS_KEYWORDS = [
    "体育", "赛事", "竞技", "比赛", "运动",
    "nba", "英超", "中超", "世界杯", "奥运",
    "足球", "篮球", "排球", "乒乓球", "羽毛球",
    "网球", "高尔夫", "台球", "斯诺克", "F1"
]


async def fetch_hmtj_source() -> List[Dict]:
    source_url = "http://1080p.19860519.de5.net/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "http://1080p.19860519.de5.net/",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url, timeout=15, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ 新源返回 HTTP {resp.status}")
                    return []
                content = await resp.text()
                data = json.loads(content)
                
                channels = []
                for item in data.get("list", []):
                    if item.get("vod_id") == "live_promo":
                        continue
                    play_url_raw = item.get("vod_play_url", "")
                    url = extract_play_url(play_url_raw)
                    if not url:
                        continue
                    channels.append({
                        "name": item.get("vod_name", ""),
                        "url": url,
                        "group_title": item.get("vod_remarks", ""),
                        "tvg_id": "",
                        "tvg_logo": item.get("vod_pic", ""),
                    })
                logger.info(f"✅ 从新源解析到 {len(channels)} 个频道")
                return channels
    except Exception as e:
        logger.error(f"❌ 拉取新源失败: {e}")
        return []


def extract_play_url(play_url_raw: str) -> Optional[str]:
    if not play_url_raw:
        return None
    parts = play_url_raw.split("$")
    if len(parts) >= 2:
        for part in parts[1:]:
            if part.startswith(("http://", "https://")):
                return part
    return None


def classify_hmtj_channel(channel: Dict) -> Optional[str]:
    group_title = channel.get("group_title", "")
    for src_cat, demo_cat in CATEGORY_MAP.items():
        if group_title == src_cat or group_title == demo_cat:
            return demo_cat
    
    name = channel.get("name", "")
    name_lower = name.lower()
    for kw in SPORTS_KEYWORDS:
        if kw in name_lower:
            return "体育赛事"
    return None


async def integrate_hmtj_source() -> Dict[str, int]:
    """
    拉取新源，分类并存入稳定源（标记为固定源）
    返回各分类的入库数量统计
    """
    channels = await fetch_hmtj_source()
    if not channels:
        return {}

    from src.stable.manager import StableManager
    stable_mgr = StableManager()
    
    stats = {"央视": 0, "卫视": 0, "地方": 0, "体育赛事": 0}
    added = 0

    for ch in channels:
        cat = classify_hmtj_channel(ch)
        if cat not in stats:
            continue
        name = ch.get("name")
        url = ch.get("url")
        if not name or not url:
            continue
        
        # 如果该频道已有固定源，则跳过（保留现有）
        existing = stable_mgr.stable_sources.get(name)
        if existing and existing.is_fixed:
            continue
        
        # 存入稳定源，标记为固定源
        stable_mgr.set_fixed_source(name, url)
        stats[cat] += 1
        added += 1
        logger.debug(f"📌 存入稳定源: {name} -> {url}")

    logger.info(f"📊 新源入库统计: 央视 {stats['央视']}，卫视 {stats['卫视']}，地方 {stats['地方']}，体育赛事 {stats['体育赛事']}，共新增 {added} 个固定源")
    return stats
