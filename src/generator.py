# src/generator.py
# 输出 M3U 和 TXT 文件模块

from pathlib import Path
from typing import List, Dict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 M3U8 格式文件，按分类写入"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # 直接遍历传入的所有分类，保留原始分类名
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            # 写入分类注释行（用于播放器分组）
            f.write(f'\n#EXTINF:-1 group-title="{cat}",{cat}\n')
            for ch in channels:
                # 取第一个 url（也可根据需要输出多个，但标准 M3U 每行一个 url）
                url = ch.get("urls", [ch.get("url")])[0]
                tvg_id = ch.get("id", "")
                tvg_logo = ch.get("logo", "")
                group = ch.get("group_title", cat)
                name = ch["name"]
                extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'
                f.write(f"{extinf}\n{url}\n")
    logger.info(f"✅ M3U 文件已生成: {output_path}")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 TXT 格式（分类 + 频道名），用于展示"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for cat, channels in channels_by_category.items():
            if not channels:
                continue
            f.write(f"\n{cat},#genre#\n")
            for ch in channels:
                f.write(f"{ch['name']}\n")
    logger.info(f"✅ TXT 文件已生成: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    """
    ordered_channels 每个元素应包含 'demo_category' 字段（由 demo_filter 添加）
    根据 demo_category 重新分组并输出。
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 按 demo_category 分组
    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    # 可对分类进行排序（保持原 demo.txt 顺序大致不变，按首次出现顺序）
    # 由于 dict 在 Python 3.7+ 保持插入顺序，我们可以按照 demos 出现的顺序来插入
    # 但 groups 是无序的，我们可以从 demo_order 中获取顺序并重新构建 groups_ordered
    # 简单起见，按分类名字典序排序，也可保持可读性
    sorted_cats = sorted(groups.keys())
    final_groups = {cat: groups[cat] for cat in sorted_cats}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(final_groups, OUTPUT_DIR / M3U_FILE)
    generate_txt(final_groups, OUTPUT_DIR / TXT_FILE)
