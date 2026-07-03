# src/hmtj_source.py
"""处理 http://1080p.19860519.de5.net/live.m3u 源的采集与分类"""

import aiohttp
import re
from typing import List, Dict, Tuple
from src.logger import logger
from src.config import OUTPUT_DIR
from src.parser import parse_m3u


async def fetch_hmtj_source() -> List[Dict]:
    """拉取新源的 M3U 内容并解析"""
    source_url = "http://1080p.19860519.de5.net/live.m3u"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url, timeout=15, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ 新源返回 HTTP {resp.status}")
                    return []
                content = await resp.text()
                # 复用现有的 M3U 解析器
                channels = parse_m3u(content)
                logger.info(f"✅ 从新源解析到 {len(channels)} 个频道")
                return channels
    except Exception as e:
        logger.error(f"❌ 拉取新源失败: {e}")
        return []


def classify_hmtj_channel(channel: Dict) -> str:
    """
    对从新源解析出的单个频道进行分类
    返回: '央视', '卫视', '地方', '体育赛事', 或 None
    """
    name = channel.get("name", "")
    name_lower = name.lower()
    
    # 1. 央视分类：匹配 CCTV 或 央视
    if re.search(r'cctv|央视', name_lower):
        return "央视"
    
    # 2. 卫视分类：匹配 卫视 或 省级卫星频道名称
    satellite_keywords = [
        "卫视", "东方卫视", "北京卫视", "湖南卫视", "浙江卫视", "江苏卫视",
        "广东卫视", "深圳卫视", "天津卫视", "山东卫视", "安徽卫视",
        "湖北卫视", "黑龙江卫视", "江西卫视", "河南卫视", "河北卫视",
        "山西卫视", "陕西卫视", "甘肃卫视", "宁夏卫视", "青海卫视",
        "云南卫视", "贵州卫视", "广西卫视", "内蒙古卫视", "新疆卫视",
        "西藏卫视", "海南卫视", "东南卫视", "重庆卫视", "四川卫视",
        "辽宁卫视", "吉林卫视", "厦门卫视"
    ]
    for kw in satellite_keywords:
        if kw in name:
            return "卫视"
    
    # 3. 省市地方频道：匹配省份或城市名（排除已匹配的卫视）
    provinces = [
        "北京", "上海", "广东", "浙江", "江苏", "湖南", "湖北",
        "山东", "河南", "四川", "福建", "安徽", "辽宁", "陕西",
        "河北", "江西", "黑龙江", "吉林", "山西", "云南", "贵州",
        "甘肃", "海南", "青海", "宁夏", "新疆", "西藏", "广西",
        "内蒙古", "香港", "澳门", "台湾"
    ]
    for prov in provinces:
        if prov in name:
            # 进一步检查是否包含"新闻"、"综合"、"生活"等地方台常见词
            if any(kw in name for kw in ["新闻", "综合", "生活", "影视", "少儿", "公共", "经济", "科教", "文艺", "频道"]):
                return "地方"
    
    # 4. 体育赛事分类：匹配体育、赛事、竞技、比赛等关键词
    sports_keywords = ["体育", "赛事", "竞技", "比赛", "运动", "NBA", "英超", "中超", "世界杯", "奥运"]
    for kw in sports_keywords:
        if kw in name:
            return "体育赛事"
    
    # 5. 如果都不匹配，返回 None（不采集）
    return None


async def integrate_hmtj_source():
    """
    主函数：拉取新源、分类、合并到现有体系
    此函数应在 run.py 的适当位置被调用
    """
    channels = await fetch_hmtj_source()
    if not channels:
        return
    
    # 分类统计
    classified = {
        "央视": [],
        "卫视": [],
        "地方": [],
        "体育赛事": []
    }
    unknown = []
    
    for ch in channels:
        cat = classify_hmtj_channel(ch)
        if cat and cat in classified:
            classified[cat].append(ch)
        else:
            unknown.append(ch)
    
    logger.info(f"📊 新源分类统计: 央视 {len(classified['央视'])}，卫视 {len(classified['卫视'])}，地方 {len(classified['地方'])}，体育赛事 {len(classified['体育赛事'])}，未分类 {len(unknown)}")
    
    # TODO: 将 classified 中的频道合并到现有的输出流程中
    # 例如，将 "央视" 分类的频道追加到现有央视分类末尾
    # 将 "体育赛事" 分类的频道追加到智能分类的体育赛事分类中
    # 具体实现需要根据你的 generator.py 和 demo_filter.py 的结构来调整
