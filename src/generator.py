# src/generator.py
# 输出 M3U 和 TXT 文件模块，支持动态追加新分类

from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict, OrderedDict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger


def build_final_order(demo_order: List[Tuple[str, str]], channels: List[dict]) -> List[Tuple[str, str]]:
    """
    构建最终输出顺序：
    1. 先按 demo_order 输出已有分类
    2. 然后追加 channels 中出现的其他分类（如 "日本频道"）
    """
    # 收集 channels 中所有分类
    categories_from_channels = set()
    for ch in channels:
        cat = ch.get("demo_category")
        if cat:
            categories_from_channels.add(cat)
    
    # 从 demo_order 中提取已有分类
    existing_categories = {cat for cat, _ in demo_order}
    
    # 找出需要追加的分类（不在 demo_order 中，但出现在 channels 中）
    extra_categories = [cat for cat in categories_from_channels if cat not in existing_categories]
    
    # 按特定顺序排序（将 "日本频道" 放在最后，其他按字母）
    # 这里简单按出现顺序追加，但为了稳定性，我们可以将 "日本频道" 放在最后
    extra_categories.sort()
    if "日本频道" in extra_categories:
        extra_categories.remove("日本频道")
        extra_categories.append("日本频道")
    
    # 构建最终顺序
    final_order = list(demo_order)  # 先复制
    for cat in extra_categories:
        # 追加一个占位条目，名称留空，后续生成时只输出分类行
        final_order.append((cat, ""))  # 空频道名表示仅输出分类行
    
    return final_order


def generate_m3u_by_order(
    channels_by_name: Dict[str, dict],
    final_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """按照 final_order 生成 M3U 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat, demo_name in final_order:
            # 如果是分类占位（无具体频道名），跳过（因为后面会通过频道输出）
            # 但我们仍然输出分类注释
            if not demo_name:
                f.write(f"\n# ----- {cat} (自动追加) -----\n")
                continue
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                clean_cat = cat.replace(",#genre#", "").strip()
                f.write(f'#EXTINF:-1 group-title="{clean_cat}",{name}\n')
                f.write(f"{url}\n")
    logger.info(f"✅ M3U 文件已生成: {output_path}")


def generate_txt_by_order(
    channels_by_name: Dict[str, dict],
    final_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """按照 final_order 生成 TXT 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        current_cat = None
        for cat, demo_name in final_order:
            clean_cat = cat.replace(",#genre#", "").strip()
            if clean_cat != current_cat:
                current_cat = clean_cat
                f.write(f"{current_cat},#genre#\n")
            # 如果是分类占位，不需要输出频道
            if not demo_name:
                continue
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                f.write(f"{name},{url}\n")
    logger.info(f"✅ TXT 文件已生成: {output_path}")


def generate_multi_m3u_by_order(
    channels_by_name: Dict[str, dict],
    final_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """生成多源 M3U 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat, demo_name in final_order:
            if not demo_name:
                f.write(f"\n# ----- {cat} (自动追加) -----\n")
                continue
            channel = channels_by_name.get(demo_name)
            if channel:
                urls = channel.get("urls", [channel.get("url")])
                valid_urls = [u for u in urls if u and u.startswith(('http://', 'https://'))]
                if valid_urls:
                    multi_url = " # ".join(valid_urls)
                    name = channel.get("name", demo_name)
                    clean_cat = cat.replace(",#genre#", "").strip()
                    f.write(f'#EXTINF:-1 group-title="{clean_cat}",{name}\n')
                    f.write(f"{multi_url}\n")
    logger.info(f"✅ 多源 M3U 文件已生成: {output_path}")


def generate_outputs_from_demo(ordered_channels: List[dict], demo_order: List[Tuple[str, str]]) -> None:
    """
    按照 demo.txt 的顺序输出，并自动追加新分类（如日本频道）
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 构建 {标准化名称: 频道数据} 的字典
    channels_by_name = {ch["name"]: ch for ch in ordered_channels}
    # 同时使用 demo_name 作为备用键
    for ch in ordered_channels:
        if "demo_name" in ch:
            channels_by_name[ch["demo_name"]] = ch

    # 构建最终输出顺序
    final_order = build_final_order(demo_order, ordered_channels)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成标准 M3U 文件
    generate_m3u_by_order(channels_by_name, final_order, OUTPUT_DIR / M3U_FILE)
    
    # 生成 TXT 文件
    generate_txt_by_order(channels_by_name, final_order, OUTPUT_DIR / TXT_FILE)
    
    # 生成多源 M3U 文件
    generate_multi_m3u_by_order(channels_by_name, final_order, OUTPUT_DIR / "tv_multi.m3u")
