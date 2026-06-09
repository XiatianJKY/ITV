# src/generator.py
# 输出 M3U 和 TXT 文件模块，支持多源备用和延迟排序

from pathlib import Path
from typing import List, Dict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE, SORT_M3U_BY_LATENCY
from src.logger import logger

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """
    生成标准 M3U8 格式文件
    - 支持多源备用（每个频道可包含多个 URL）
    - 按延迟排序（最佳源在前）
    - 保持分类顺序
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write("# 提示：此列表已按延迟排序，第一个 URL 为最佳源\n")
        f.write("# 如果播放卡顿，请尝试增加播放器网络缓存（建议 5-10 秒）\n\n")
        
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            
            # 如果启用，对当前分类内的频道按延迟排序
            if SORT_M3U_BY_LATENCY:
                channels = sorted(channels, key=lambda x: x.get("latency", 9999))
            
            # 写入分类注释（部分播放器会识别为分组标题）
            f.write(f"# 分类: {cat}\n")
            
            for ch in channels:
                name = ch["name"]
                urls = ch.get("urls", [ch.get("url")])
                latency = ch.get("latency", "未知")
                
                if len(urls) == 1:
                    # 单源：标准格式
                    extinf = f'#EXTINF:-1 tvg-id="{ch.get("id", "")}" tvg-logo="{ch.get("logo", "")}" group-title="{cat}" latency="{latency}ms",{name}'
                    f.write(f"{extinf}\n{urls[0]}\n")
                else:
                    # 多源：列出所有备用源，第一个为最佳
                    f.write(f"# 频道 {name} 有 {len(urls)} 个备用源（延迟 {latency}ms）\n")
                    for i, url in enumerate(urls):
                        suffix = "" if i == 0 else f" (备用{i})"
                        extinf = f'#EXTINF:-1 tvg-id="{ch.get("id", "")}" tvg-logo="{ch.get("logo", "")}" group-title="{cat}" latency="{ch.get("latency", "未知")}ms",{name}{suffix}'
                        f.write(f"{extinf}\n{url}\n")
    
    total_channels = sum(len(ch) for ch in channels_by_category.values())
    logger.info(f"✅ M3U 文件已生成: {output_path} (共 {total_channels} 个频道)")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 TXT 文件，格式与 demo.txt 兼容，保持传入的分类顺序"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# IPTV 播放列表\n")
        f.write("# 格式: 频道名,URL\n")
        f.write("# 提示: 如播放卡顿，请使用第一个 URL（延迟最低）\n\n")
        
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            
            # 对当前分类内的频道按延迟排序
            if SORT_M3U_BY_LATENCY:
                channels = sorted(channels, key=lambda x: x.get("latency", 9999))
            
            f.write(f"\n{cat},#genre#\n")
            for ch in channels:
                # 取第一个 URL（最佳源）
                url = ch.get("urls", [ch.get("url")])[0]
                latency = ch.get("latency", "未知")
                f.write(f"{ch['name']},{url}  # 延迟: {latency}ms\n")
    
    total_channels = sum(len(ch) for ch in channels_by_category.values())
    logger.info(f"✅ TXT 文件已生成: {output_path} (共 {total_channels} 个频道)")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    """
    ordered_channels 已按照 demo.txt 的顺序排列（包含 demo_category 字段）
    按 demo_category 分组后输出 M3U 和 TXT
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 按 demo_category 分组，保持插入顺序
    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    # 统计分组信息
    for cat, channels in groups.items():
        logger.info(f"📂 分类 '{cat}': {len(channels)} 个频道")
        if channels:
            avg_latency = sum(ch.get("latency", 0) for ch in channels) / len(channels)
            logger.info(f"   平均延迟: {avg_latency:.0f}ms")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(groups, OUTPUT_DIR / M3U_FILE)
    generate_txt(groups, OUTPUT_DIR / TXT_FILE)
