# src/generator.py
# 输出 M3U 和 TXT 文件模块，按 demo.txt 顺序输出，并追加未匹配的港澳台日频道

from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger


def generate_m3u_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    extra_channels: List[dict],
    output_path: Path
) -> None:
    """生成 M3U 文件，先输出 demo 顺序，再追加 extra_channels"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # 1. 输出 demo 中的频道
        for cat, demo_name in demo_order:
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                clean_cat = cat.replace(",#genre#", "").strip()
                f.write(f'#EXTINF:-1 group-title="{clean_cat}",{name}\n')
                f.write(f"{url}\n")
        
        # 2. 追加额外的频道（按分类分组）
        if extra_channels:
            f.write("\n# ===== 以下为自动追加的港澳台日频道 =====\n")
            # 按分类分组
            grouped = defaultdict(list)
            for ch in extra_channels:
                cat = ch.get("demo_category", "港澳台日")
                grouped[cat].append(ch)
            
            for cat, channels in grouped.items():
                f.write(f"\n# ----- {cat} -----\n")
                for ch in channels:
                    url = ch.get("urls", [ch.get("url")])[0]
                    name = ch.get("name")
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n')
                    f.write(f"{url}\n")
    
    logger.info(f"✅ M3U 文件已生成: {output_path}")


def generate_txt_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    extra_channels: List[dict],
    output_path: Path
) -> None:
    """生成 TXT 文件，先输出 demo 顺序，再追加 extra_channels"""
    with open(output_path, 'w', encoding='utf-8') as f:
        current_cat = None
        # 1. 输出 demo 中的频道
        for cat, demo_name in demo_order:
            clean_cat = cat.replace(",#genre#", "").strip()
            if clean_cat != current_cat:
                current_cat = clean_cat
                f.write(f"{current_cat},#genre#\n")
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                f.write(f"{name},{url}\n")
        
        # 2. 追加额外的频道（按分类分组）
        if extra_channels:
            f.write("\n# ===== 以下为自动追加的港澳台日频道 =====\n")
            grouped = defaultdict(list)
            for ch in extra_channels:
                cat = ch.get("demo_category", "港澳台日")
                grouped[cat].append(ch)
            
            for cat, channels in grouped.items():
                f.write(f"\n{cat},#genre#\n")
                for ch in channels:
                    url = ch.get("urls", [ch.get("url")])[0]
                    name = ch.get("name")
                    f.write(f"{name},{url}\n")
    
    logger.info(f"✅ TXT 文件已生成: {output_path}")


def generate_multi_m3u_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    extra_channels: List[dict],
    output_path: Path
) -> None:
    """生成多源 M3U 文件，支持自动切换，同样追加 extra_channels"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # 1. demo 频道
        for cat, demo_name in demo_order:
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
        
        # 2. 额外频道
        if extra_channels:
            f.write("\n# ===== 以下为自动追加的港澳台日频道 =====\n")
            grouped = defaultdict(list)
            for ch in extra_channels:
                cat = ch.get("demo_category", "港澳台日")
                grouped[cat].append(ch)
            
            for cat, channels in grouped.items():
                f.write(f"\n# ----- {cat} -----\n")
                for ch in channels:
                    url = ch.get("urls", [ch.get("url")])[0]
                    name = ch.get("name")
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n')
                    f.write(f"{url}\n")
    
    logger.info(f"✅ 多源 M3U 文件已生成: {output_path}")


def generate_outputs_from_demo(ordered_channels: List[dict], demo_order: List[Tuple[str, str]]) -> None:
    """按照 demo.txt 的顺序输出 M3U 和 TXT 文件，并自动追加未匹配的港澳台日频道"""
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 分离：匹配的频道和额外追加的频道（demo_category 不在 demo_order 中的分类）
    # 这里简单地根据是否有 demo_category 且存在于 demo_order 来判断
    # 实际上，demo_order 中可能没有这些分类，所以我们将所有频道放入 channels_by_name，然后通过 extra_channels 传递那些不在 demo_order 中的频道
    demo_categories = {cat for cat, _ in demo_order}
    channels_by_name = {}
    extra_channels = []
    
    for ch in ordered_channels:
        name = ch.get("name")
        if not name:
            continue
        channels_by_name[name] = ch
        # 如果该频道的分类不在 demo_order 中，且不是常规分类（央视、卫视等），则视为额外频道
        cat = ch.get("demo_category", "")
        if cat and cat not in demo_categories and cat not in ["央视", "卫视", "地方", "港澳台", "其他"]:
            extra_channels.append(ch)
        # 对于港澳台日分类，即使 demo_order 可能包含"港澳台"分类，但我们希望单独追加，所以也放入 extra
        # 但注意 demo_order 中可能有"港澳台"分类，如果有了，就不需要重复追加
        # 这里简化：只要分类不在 demo_categories 中，就放入 extra
        # 同时要排除那些已经匹配过的频道（即 name 在 demo_order 中）
        # 但 ordered_channels 已经经过 filter_and_order_by_demo 处理，其中匹配的频道都有 demo_category 对应 demo_order 中的分类
        # 所以这里直接根据是否在 demo_categories 来判断
        # 但可能存在 demo_category 为 "香港频道" 但 demo_order 中没有 "香港频道" 的情况，所以需要追加
    
    # 修正：从 ordered_channels 中提取真正需要追加的频道（其分类不在 demo_categories 中）
    extra_channels = [
        ch for ch in ordered_channels
        if ch.get("demo_category") and ch.get("demo_category") not in demo_categories
    ]
    
    # 同时，对于已经匹配的频道（demo_category 在 demo_categories 中），它们已经在 channels_by_name 中
    # 但 channels_by_name 可能包含所有频道，所以没问题
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成标准 M3U 文件
    generate_m3u_by_demo_order(
        channels_by_name, demo_order, extra_channels, OUTPUT_DIR / M3U_FILE
    )
    
    # 生成 TXT 文件
    generate_txt_by_demo_order(
        channels_by_name, demo_order, extra_channels, OUTPUT_DIR / TXT_FILE
    )
    
    # 生成多源 M3U 文件
    generate_multi_m3u_by_demo_order(
        channels_by_name, demo_order, extra_channels, OUTPUT_DIR / "tv_multi.m3u"
    )
