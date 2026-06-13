# src/overseas_filter.py
"""国外频道筛选和分类模块"""

import re
from collections import defaultdict
from typing import List, Dict, Tuple
from pathlib import Path

from src.config import OUTPUT_DIR
from src.logger import logger


# 国家/地区关键词映射
COUNTRY_KEYWORDS = {
    "美国": ["us", "usa", "united states", "america", "american", "abc", "nbc", "cbs", "cnn", "fox", "msnbc", "hbo", "discovery", "national geographic", "history", "a&e", "animal planet", "tlc", "usa", "american"],
    "英国": ["uk", "united kingdom", "britain", "british", "bbc", "sky news", "itv", "channel 4", "channel 5", "british"],
    "日本": ["jp", "japan", "japanese", "nhk", "fuji tv", "tbs", "tv asahi", "ntv", "tokyo mx", "japan"],
    "韩国": ["kr", "korea", "korean", "kbs", "mbc", "sbs", "tvN", "jtbc", "arirang", "korea"],
    "法国": ["fr", "france", "french", "france 2", "france 3", "tf1", "m6", "french"],
    "德国": ["de", "germany", "german", "ard", "zdf", "rtl", "pro7", "sat.1", "german"],
    "俄罗斯": ["ru", "russia", "russian", "rt ", "russia today", "russian"],
    "意大利": ["it", "italy", "italian", "rai", "mediaset", "italian"],
    "西班牙": ["es", "spain", "spanish", "rtve", "antena 3", "la sexta", "spanish"],
    "印度": ["in", "india", "indian", "zee", "star plus", "sony tv", "colors", "india"],
    "澳大利亚": ["au", "australia", "australian", "abc australia", "sbs", "seven network", "nine network", "australian"],
    "加拿大": ["ca", "canada", "canadian", "cbc", "ctv", "global tv", "canadian"],
    "巴西": ["br", "brazil", "brazilian", "globo", "record tv", "brazilian"],
    "中东": ["ae", "saudi", "qatar", "dubai", "al jazeera", "beIN", "middle east", "arab"],
    "东南亚": ["th", "thailand", "vn", "vietnam", "my", "malaysia", "id", "indonesia", "ph", "philippines", "thai", "vietnamese", "malay", "indonesian", "filipino"],
    "欧洲": ["eu", "europe", "european", "euronews", "europe"],
    "非洲": ["africa", "african", "south africa", "nigeria", "kenya", "african"],
    "其他": [],  # 默认分类
}

# 语言/类型分类
LANGUAGE_CATEGORIES = {
    "英语": ["english", "bbc", "cnn", "fox", "abc", "nbc", "cbs", "sky news"],
    "华语": ["chinese", "mandarin", "cantonese", "粤语", "国语"],
    "日语": ["japanese", "日语"],
    "韩语": ["korean", "韩语"],
    "俄语": ["russian", "俄语"],
    "法语": ["french", "法语"],
    "德语": ["german", "德语"],
    "西班牙语": ["spanish", "español"],
    "阿拉伯语": ["arabic", "عربي"],
}

# 内容类型分类
CONTENT_CATEGORIES = {
    "新闻": ["news", "bbc", "cnn", "fox news", "sky news", "al jazeera", "france 24", "euronews", "rt news", "cgtn"],
    "体育": ["sport", "espn", "sky sport", "fox sport", "bein sport", "nba", "nfl", "uefa", "fifa"],
    "电影": ["movie", "cinema", "film", "hbo", "showtime", "starz", "paramount"],
    "娱乐": ["entertainment", "mtv", "e!", "vH1", "comedy", "syfy", "fx"],
    "纪录片": ["documentary", "discovery", "national geographic", "history", "animal planet", "nat geo"],
    "音乐": ["music", "mtv", "vH1", "fuse", "music"],
    "儿童": ["kids", "cartoon", "disney", "nickelodeon", "cartoon network", "baby", "children"],
    "财经": ["business", "bloomberg", "cnbc", "fox business", "money"],
    "生活": ["lifestyle", "travel", "food", "home", "garden", "fashion", "health"],
}


def detect_country(channel_name: str) -> str:
    """检测频道所属国家"""
    name_lower = channel_name.lower()
    
    for country, keywords in COUNTRY_KEYWORDS.items():
        if country == "其他":
            continue
        for kw in keywords:
            if kw in name_lower:
                return country
    return "其他"


def detect_language(channel_name: str) -> str:
    """检测频道语言"""
    name_lower = channel_name.lower()
    
    for lang, keywords in LANGUAGE_CATEGORIES.items():
        for kw in keywords:
            if kw in name_lower:
                return lang
    return "其他"


def detect_content_type(channel_name: str) -> str:
    """检测频道内容类型"""
    name_lower = channel_name.lower()
    
    for content_type, keywords in CONTENT_CATEGORIES.items():
        for kw in keywords:
            if kw in name_lower:
                return content_type
    return "综合"


def classify_overseas_channels(unmatched_channels: List[Dict]) -> Dict[str, List[Dict]]:
    """对未匹配的频道进行分类（主要是国外频道）"""
    classified = defaultdict(list)
    
    for ch in unmatched_channels:
        name = ch.get("name", "")
        # 跳过中文频道（央视、卫视、地方台）
        if re.search(r'[央视CCTV卫视台]', name):
            # 但保留 CGTN 等国际频道
            if "CGTN" not in name.upper():
                continue
        
        # 分类
        country = detect_country(name)
        language = detect_language(name)
        content_type = detect_content_type(name)
        
        # 存储分类信息
        ch["country"] = country
        ch["language"] = language
        ch["content_type"] = content_type
        
        # 按国家分类
        classified[country].append(ch)
    
    # 每个国家内按频道名排序
    for country in classified:
        classified[country].sort(key=lambda x: x["name"])
    
    return dict(classified)


def generate_overseas_output(classified_channels: Dict[str, List[Dict]], output_dir: Path = OUTPUT_DIR):
    """生成国外频道输出文件"""
    if not classified_channels:
        logger.info("没有国外频道需要输出")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 生成 M3U 文件
    m3u_path = output_dir / "guowai.m3u"
    with open(m3u_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write("# 国外频道合集 (Overseas Channels)\n")
        f.write(f"# 共 {sum(len(v) for v in classified_channels.values())} 个频道\n")
        f.write("# 按国家/地区分类\n\n")
        
        for country, channels in sorted(classified_channels.items()):
            f.write(f"\n# ========== {country} ({len(channels)}个频道) ==========\n")
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                # 添加分类标签到 group-title
                group = f"{country}·{ch.get('content_type', '综合')}"
                f.write(f'#EXTINF:-1 group-title="{group}",{ch["name"]}\n{url}\n')
    
    logger.info(f"✅ 国外频道 M3U 已生成: {m3u_path}")
    
    # 2. 生成 TXT 文件（按国家分节）
    txt_path = output_dir / "guowai.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("# 国外频道列表 (按国家分类)\n")
        f.write(f"# 共 {sum(len(v) for v in classified_channels.values())} 个频道\n\n")
        
        for country, channels in sorted(classified_channels.items()):
            f.write(f"\n{country}频道,#genre#\n")
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]
                f.write(f"{ch['name']},{url}\n")
    
    logger.info(f"✅ 国外频道 TXT 已生成: {txt_path}")
    
    # 3. 生成 JSON 统计文件
    json_path = output_dir / "guowai_stats.json"
    import json
    import datetime
    
    stats = {
        "total": sum(len(v) for v in classified_channels.values()),
        "generated": datetime.datetime.now().isoformat(),
        "by_country": {country: len(channels) for country, channels in classified_channels.items()},
        "by_language": {},
        "by_content_type": {}
    }
    
    # 统计语言分布
    for channels in classified_channels.values():
        for ch in channels:
            lang = ch.get("language", "其他")
            stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
            ctype = ch.get("content_type", "综合")
            stats["by_content_type"][ctype] = stats["by_content_type"].get(ctype, 0) + 1
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ 国外频道统计已生成: {json_path}")
    
    # 4. 打印统计信息
    logger.info("\n🌍 国外频道统计:")
    for country, channels in sorted(classified_channels.items(), key=lambda x: len(x[1]), reverse=True):
        logger.info(f"  {country}: {len(channels)} 个频道")


def process_overseas_channels(unmatched_channels: List[Dict], output_dir: Path = OUTPUT_DIR) -> Dict:
    """处理国外频道：分类并输出"""
    if not unmatched_channels:
        logger.info("没有未匹配的频道")
        return {}
    
    logger.info(f"🌍 正在处理 {len(unmatched_channels)} 个未匹配频道...")
    
    # 分类
    classified = classify_overseas_channels(unmatched_channels)
    
    # 输出
    generate_overseas_output(classified, output_dir)
    
    return classified
