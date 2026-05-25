# src/merger.py
# 频道合并模块：按标准化名称合并，优先选择 URL 与频道数字匹配的源

import re
from collections import defaultdict
from src.config import MAX_SOURCES_PER_CHANNEL

def normalize_channel_name(name: str) -> str:
    """标准化频道名，用于合并分组"""
    name = re.sub(r'\s*(?:1080[pi]|720[pi]|4K|8K|HD|高清|超清|标清|流畅|付费|备\d*)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'(?i)^CCTV\s*(\d+)$', r'CCTV-\1', name)
    name = re.sub(r'(?i)^CCTV\s*(\d+)\+$', r'CCTV-\1+', name)
    return name

def extract_channel_number(name: str) -> str:
    """从频道名中提取数字（如 CCTV-1 -> 1）"""
    match = re.search(r'CCTV[- ]?(\d+)', name, re.IGNORECASE)
    return match.group(1) if match else None

def url_contains_number(url: str, number: str) -> bool:
    """检查 URL 中是否包含特定数字（如 /1/ 或 1.m3u8）"""
    if not number:
        return False
    # 常见模式：/1/ , /1.m3u8 , _1_ , cctv1
    patterns = [rf'[/_]?{number}[/_]', rf'cctv{number}', rf'channel/{number}', rf'{number}\.m3u8']
    for pat in patterns:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False

def merge_channels_by_name(valid_channels: list) -> list:
    groups = defaultdict(list)
    for ch in valid_channels:
        norm_name = normalize_channel_name(ch["name"])
        groups[norm_name].append(ch)

    merged = []
    for norm_name, ch_list in groups.items():
        # 提取频道数字（如果有）
        channel_num = extract_channel_number(norm_name)

        def sort_key(ch):
            # 优先规则：
            # 1. 如果频道数字存在，且 URL 中包含该数字，则优先级最高（codec 无效时）
            # 2. 否则按 codec 和延迟排序
            url = ch.get("url", "")
            num_match = 1 if (channel_num and url_contains_number(url, channel_num)) else 0
            codec = ch.get("video_codec", "")
            codec_priority = 0 if codec == "h264" else 1 if codec == "hevc" else 2
            latency = ch.get("latency", 9999)
            # 返回元组：优先数字匹配，然后编码，最后延迟
            return (-num_match, codec_priority, latency)

        ch_list.sort(key=sort_key)
        top = ch_list[:MAX_SOURCES_PER_CHANNEL]
        primary = top[0]
        merged_ch = {
            "name": primary["name"],
            "urls": [c["url"] for c in top],
            "url": primary["url"],
            "latency": primary["latency"],
            "video_codec": primary["video_codec"],
            "group_title": primary.get("group_title", ""),
            "id": primary.get("tvg_id", ""),
            "logo": primary.get("tvg_logo", ""),
            "ip_info": primary.get("ip_info")
        }
        merged.append(merged_ch)

    print(f"🔄 频道合并完成：{len(valid_channels)} 个源 -> {len(merged)} 个频道（已优先匹配数字URL）")
    return merged
