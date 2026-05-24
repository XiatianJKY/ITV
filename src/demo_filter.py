# src/demo_filter.py
# Demo 频道筛选与排序模块，支持别名匹配

import re
from pathlib import Path
from typing import List, Tuple
from src.config import DEMO_FILE
from src.alias_matcher import get_alias_matcher

def parse_demo_order(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    """解析 demo.txt，返回 [(分类, 标准化频道名), ...]"""
    if not demo_file.exists():
        print(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    matcher = get_alias_matcher()
    order = []
    current_category = None
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(",#genre#"):
                current_category = line[:-7]
                continue
            if line.startswith('#'):
                continue
            if current_category is not None:
                # 对 demo 中的频道名也应用别名标准化
                demo_name = line
                if matcher:
                    demo_name = matcher.normalize(demo_name)
                order.append((current_category, demo_name))
            else:
                order.append(("其他", line))
    print(f"📋 从 demo.txt 解析到 {len(order)} 个有序频道（已标准化）")
    return order

def filter_and_order_by_demo(channels: list, alias_matcher=None) -> list:
    """根据 demo.txt 筛选并排序频道，返回按 demo 顺序排列的频道列表"""
    demo_order = parse_demo_order()
    if not demo_order:
        return channels
    
    # 建立标准化名称到频道的映射（注意 channels 中的 name 已经是标准化后的）
    index = {ch["name"]: ch for ch in channels}
    matched = []
    for category, demo_name in demo_order:
        if demo_name in index:
            matched.append(index[demo_name])
            # 可选：删除已匹配的，避免重复（但 demo 中同一名称只会出现一次）
    print(f"🎯 Demo 筛选：原始 {len(channels)} 个频道 -> 匹配 {len(matched)} 个频道（按 demo 顺序）")
    return matched
