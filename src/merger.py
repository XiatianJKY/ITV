# src/merger.py
# 频道合并模块，H.264优先 + 延迟排序 + 固定源优先

import re
import copy
from collections import defaultdict
from src.config import MAX_SOURCES_PER_CHANNEL
from src.logo_matcher import get_logo_matcher
from src.logger import logger


def normalize_channel_name(name: str) -> str:
    """标准化频道名，去除清晰度标签和括号内容"""
    name = re.sub(r'\s*(?:1080[pi]|720[pi]|4K|8K|HD|高清|超清|标清|流畅|付费|备\d*|备用\d*|备播|备源)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    name = re.sub(r'[备用备播备源]+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def is_cctv5plus(name: str) -> bool:
    """判断是否为 CCTV-5+ 频道"""
    name_lower = name.lower()
    if '+' in name or '＋' in name:
        return True
    if '5plus' in name_lower or '5+' in name_lower:
        return True
    if '央视5+' in name or '中央5+' in name:
        return True
    return False


def is_cctv5(name: str) -> bool:
    """判断是否为 CCTV-5 频道（排除 CCTV-5+）"""
    name_lower = name.lower()
    if '+' in name or '＋' in name:
        return False
    if '5plus' in name_lower:
        return False
    if re.search(r'cctv[-\s]*5\b', name_lower):
        return True
    if '央视5' in name or '中央5' in name:
        return True
    return False


def get_cctv_standard_name(name: str) -> str:
    """
    将央视频道名转换为标准格式
    优先处理 CCTV-5+，然后是 CCTV-5，最后是其他数字
    """
    name_clean = re.sub(r'\s*\([^)]*\)', '', name)  # 移除括号内容
    name_lower = name_clean.lower()
    
    # 1. 优先匹配 CCTV-5+（必须包含加号）
    if re.search(r'cctv[-\s]*5\s*[＋\+]', name_lower):
        return "CCTV-5+"
    if is_cctv5plus(name_clean):
        return "CCTV-5+"
    
    # 2. 匹配 CCTV-5（不包含加号，且不包含 plus）
    if is_cctv5(name_clean):
        return "CCTV-5"
    
    # 3. 其他 CCTV-数字
    match = re.search(r'cctv[-\s]*(\d+)', name_lower)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 17:
            return f"CCTV-{num}"
    
    # 4. 央视+数字
    match = re.search(r'央视[-\s]*(\d+)', name_clean)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 17:
            return f"CCTV-{num}"
    
    return None


def get_channel_quality_score(channel: dict) -> tuple:
    """获取频道质量评分（固定源优先级最高）"""
    # 固定源优先级 0（最高）
    if channel.get("is_fixed"):
        return (0, 0, 0)
    
    codec = channel.get("video_codec", "").lower()
    if codec == "h264":
        codec_priority = 1
    elif codec in ["hevc", "h265"]:
        codec_priority = 2
    else:
        codec_priority = 3
    
    latency = channel.get("latency", 9999)
    
    # URL 稳定性评分
    url = channel.get("url", "").lower()
    url_bonus = 0
    if ".m3u8" in url:
        url_bonus = 0
    elif ".ts" in url:
        url_bonus = 1
    else:
        url_bonus = 2
    
    return (codec_priority, latency, url_bonus)


def merge_channels_by_name(valid_channels: list) -> list:
    """合并频道，确保所有固定源被保留，CCTV-5 不被覆盖"""
    groups = defaultdict(list)
    
    # 首先添加固定源（来自 fixed_sources.py）
    from src.fixed_sources import CCTV_FIXED_SOURCES, ENABLE_FIXED_SOURCES, FIXED_SOURCE_LATENCY, FIXED_SOURCE_CODEC
    fixed_sources_added = set()
    
    if ENABLE_FIXED_SOURCES:
        for std_name, url in CCTV_FIXED_SOURCES.items():
            if url:
                # 检查是否已经有该频道的源在 valid_channels 中
                # 但为了确保固定源被优先使用，我们直接插入一个固定源记录到 groups
                # 但 groups 是在遍历 valid_channels 时构建的，所以我们需要在遍历前处理
                # 更简单：在遍历 valid_channels 时，为每个频道检查是否有对应的固定源
                pass  # 后续在循环中处理
    
    # 分组
    for ch in valid_channels:
        raw_name = ch["name"]
        std_name = get_cctv_standard_name(raw_name)
        if std_name:
            norm_name = std_name
        else:
            norm_name = normalize_channel_name(raw_name)
            if not norm_name or len(norm_name) < 2:
                norm_name = raw_name
        groups[norm_name].append(ch)
    
    # 现在为每个 group 检查是否有固定源，如果有且未添加，则插入到最前面
    if ENABLE_FIXED_SOURCES:
        from src.fixed_sources import CCTV_FIXED_SOURCES, FIXED_SOURCE_LATENCY, FIXED_SOURCE_CODEC
        for std_name, url in CCTV_FIXED_SOURCES.items():
            if not url:
                continue
            if std_name in groups:
                # 检查是否已经有固定源标记
                has_fixed = any(ch.get("is_fixed") for ch in groups[std_name])
                if not has_fixed:
                    # 在列表最前面插入固定源
                    fixed_ch = {
                        "name": std_name,
                        "url": url,
                        "latency": FIXED_SOURCE_LATENCY,
                        "video_codec": FIXED_SOURCE_CODEC,
                        "is_fixed": True,
                        "group_title": "央视",
                        "tvg_id": "",
                        "tvg_logo": "",
                    }
                    groups[std_name].insert(0, fixed_ch)
                    logger.info(f"📌 为 {std_name} 插入固定源: {url}")
            else:
                # 该频道在 valid_channels 中不存在，但固定源存在，需要创建
                fixed_ch = {
                    "name": std_name,
                    "url": url,
                    "latency": FIXED_SOURCE_LATENCY,
                    "video_codec": FIXED_SOURCE_CODEC,
                    "is_fixed": True,
                    "group_title": "央视",
                    "tvg_id": "",
                    "tvg_logo": "",
                }
                groups[std_name] = [fixed_ch]
                logger.info(f"📌 创建新频道并插入固定源: {std_name} -> {url}")
    
    logo_matcher = get_logo_matcher()
    merged = []
    
    for norm_name, ch_list in groups.items():
        # 去重（基于URL）
        seen_urls = set()
        unique_list = []
        for ch in ch_list:
            if ch["url"] not in seen_urls:
                seen_urls.add(ch["url"])
                unique_list.append(ch)
        
        # 按质量评分排序
        unique_list.sort(key=get_channel_quality_score)
        
        # 取前 MAX_SOURCES_PER_CHANNEL 个
        top = unique_list[:MAX_SOURCES_PER_CHANNEL]
        primary = top[0] if top else None
        
        if not primary:
            continue
        
        logo_url = primary.get("tvg_logo", "")
        if not logo_url:
            logo_url = logo_matcher.get_logo_url(norm_name)
        
        merged.append({
            "name": norm_name,
            "urls": [c["url"] for c in top],
            "url": primary["url"],
            "latency": primary.get("latency", 9999),
            "video_codec": primary.get("video_codec", ""),
            "is_fixed": primary.get("is_fixed", False),
            "group_title": primary.get("group_title", "央视"),
            "id": primary.get("tvg_id", ""),
            "logo": logo_url,
        })
    
    # 统计固定源使用情况
    fixed_count = sum(_count = sum(1 for ch in merged if ch.get1 for ch in merged if ch.get("is_fixed("is_fixed"))
    if fixed_count > "))
    if fixed_count > 0:
        logger0:
        logger.info(f"📌 已使用.info(f"📌 已使用 {fixed_count} {fixed_count} 个固定优质源")
    
    # 统计 CCTV 个固定优质源")
    
    # 统计 CCTV 频道 频道
   
    cctv_channels cctv_channels = [ch for ch in = [ch for ch in merged if ch["name"]. merged if ch["name"].startswith("CCTVstartswith("CCTV-")]
   -")]
    logger.info(f" logger.info(f"📊 合并📊 合并完成:完成: 共 {len 共 {len(merged)} (merged)} 个频道个频道，其中央视 {len(cctv_channels)}，其中央视 {len(cctv_channels)} 个 个")
    
    return merged")
    
    return merged
