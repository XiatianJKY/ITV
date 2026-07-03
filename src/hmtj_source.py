# src/hmtj_source.py
"""处理 http://1080p.19860519.de5.net/ 源的采集与分类（JSON API 版）
   功能：将新源中的频道作为优质源，与稳定池比较并替换/新增
"""

import aiohttp
import json
import re
from typing import List, Dict, Optional
from src.logger import logger
from src.stable.manager import StableManager
from src.database import channel_key


# 分类映射
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
    """拉取 JSON 数据并解析为频道列表"""
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
                        "vod_id": item.get("vod_id", ""),
                        # 假设新源质量较好，给予一个低延迟（后续可实际测速）
                        "latency": 200,  # 默认200ms，可通过实际测速更新
                        "video_codec": "h264",
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


def classify_hmtj_channel(channel: Dict) -> str:
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


async def integrate_hmtj_source() -> Dict[str, List[Dict]]:
    """
    主函数：拉取新源，并将其频道与稳定池比较，替换/新增优质源
    返回分类字典（用于可能的输出）
    """
    channels = await fetch_hmtj_source()
    if not channels:
        return {}
    
    stable_mgr = StableManager()
    classified = {
        "央视": [],
        "卫视": [],
        "地方": [],
        "体育赛事": [],
    }
    unknown = []
    replaced = 0
    added = 0
    
    for ch in channels:
        cat = classify_hmtj_channel(ch)
        if cat:
            ch["demo_category"] = cat
            ch["urls"] = [ch["url"]]
            if cat in classified:
                classified[cat].append(ch)
            else:
                unknown.append(ch)
        else:
            unknown.append(ch)
            continue
        
        # 检查稳定池中是否已有同名频道
        existing = stable_mgr.stable_sources.get(ch["name"])
        if existing:
            # 比较质量：假设新源延迟更低则替换
            new_latency = ch.get("latency", 9999)
            old_latency = existing.latency if existing.latency else 9999
            if new_latency < old_latency:
                # 替换
                stable_mgr.replace_source(ch["name"], ch["url"], new_latency, ch.get("video_codec", ""))
                replaced += 1
                logger.info(f"🔄 替换稳定源: {ch['name']} (新延迟 {new_latency}ms < 旧延迟 {old_latency}ms)")
            else:
                logger.debug(f"⏭️ 保留现有稳定源: {ch['name']} (新延迟 {new_latency}ms >= 旧延迟 {old_latency}ms)")
        else:
            # 新增到稳定池（作为普通源）
            stable_mgr.promote_candidate(ch["name"], ch["url"], ch.get("latency", 9999), ch.get("video_codec", ""))
            added += 1
            logger.info(f"➕ 新增稳定源: {ch['name']}")
    
    logger.info(f"📊 新源集成统计: 替换 {replaced} 个，新增 {added} 个，未处理 {len(unknown)}")
    logger.info(f"📊 分类统计: 央视 {len(classified['央视'])}，卫视 {len(classified['卫视'])}，地方 {len(classified['地方'])}，体育赛事 {len(classified['体育赛事'])}")
    
    # 返回分类字典，可用于后续输出（若需要）
    return {k: v for k, v in classified.items() if v}
