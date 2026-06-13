# src/generator_enhanced.py
"""增强版输出生成器：支持多种输出格式"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from src.config import OUTPUT_DIR
from src.epg_injector import get_epg_injector
from src.logger import logger


class EnhancedOutputGenerator:
    """多种输出格式生成器"""
    
    def __init__(self):
        self.epg_injector = get_epg_injector()
    
    def generate_all_outputs(
        self, 
        channels: List[Dict], 
        demo_order: List[Tuple[str, str]],
        enable_json: bool = True,
        enable_lite: bool = True,
        enable_epg: bool = True
    ) -> None:
        """生成所有格式的输出文件
        
        Args:
            channels: 频道列表
            demo_order: demo 顺序列表
            enable_json: 是否生成 JSON 输出
            enable_lite: 是否生成精简版
            enable_epg: 是否生成 EPG 版本
        """
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. 标准国内版（原有格式，由原有函数生成，这里不再重复）
        # generate_outputs_from_demo 已经在外部调用
        
        # 2. EPG 就绪版（带 tvg-id 和 logo）
        if enable_epg:
            self._generate_epg_m3u(channels, demo_order, OUTPUT_DIR / "tv_epg.m3u")
        
        # 3. JSON API 版（供其他程序调用）
        if enable_json:
            self._generate_json_api(channels, OUTPUT_DIR / "channels.json")
        
        # 4. 多源切换版（同一频道多个源）- 由原有函数生成，这里不再重复
        
        # 5. 精简手机版（只保留最稳定的源）
        if enable_lite:
            self._generate_lite_version(channels, OUTPUT_DIR / "tv_lite.m3u")
        
        logger.info("✅ 所有增强版输出完成")
    
    def _generate_epg_m3u(self, channels: List[Dict], demo_order: List[Tuple[str, str]], path: Path) -> None:
        """EPG 就绪版 M3U"""
        # 注入 EPG 元数据
        channels_with_epg = self.epg_injector.inject_epg_metadata(channels.copy())
        
        # 构建名称到频道的映射
        channels_by_name = {ch["name"]: ch for ch in channels_with_epg}
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write("# 增强版 - 带 EPG 节目单支持\n")
            
            for cat, demo_name in demo_order:
                # 尝试通过 demo_name 查找，如果没有则尝试通过标准名称查找
                channel = channels_by_name.get(demo_name)
                if not channel:
                    # 尝试模糊匹配
                    for name, ch in channels_by_name.items():
                        if name == demo_name or demo_name in name:
                            channel = ch
                            break
                
                if channel:
                    tags = []
                    if channel.get("tvg_id"):
                        tags.append(f'tvg-id="{channel["tvg_id"]}"')
                    if channel.get("logo"):
                        tags.append(f'tvg-logo="{channel["logo"]}"')
                    tags.append(f'group-title="{cat}"')
                    
                    tags_str = " ".join(tags)
                    url = channel.get("urls", [channel.get("url")])[0]
                    f.write(f'#EXTINF:-1 {tags_str},{channel["name"]}\n{url}\n')
        
        logger.info(f"✅ EPG 就绪版已生成: {path}")
    
    def _generate_json_api(self, channels: List[Dict], path: Path) -> None:
        """JSON API 格式"""
        import datetime
        
        api_data = {
            "version": "2.0",
            "total": len(channels),
            "generated": datetime.datetime.now().isoformat(),
            "channels": []
        }
        
        for ch in channels:
            channel_info = {
                "name": ch["name"],
                "urls": ch.get("urls", [ch.get("url")]),
                "latency": ch.get("latency"),
                "codec": ch.get("video_codec", ""),
                "tvg_id": ch.get("tvg_id", ""),
                "logo": ch.get("logo", ""),
                "category": ch.get("demo_category", ch.get("group_title", ""))
            }
            # 只添加非空值
            channel_info = {k: v for k, v in channel_info.items() if v}
            api_data["channels"].append(channel_info)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ JSON API 已生成: {path}")
    
    def _generate_lite_version(self, channels: List[Dict], path: Path) -> None:
        """精简版：只保留延迟最低的源（按分类限制数量）"""
        # 央视全部保留，其他分类只保留前 50 个
        lite_channels = []
        cat_counts = {}
        
        for ch in channels:
            cat = ch.get("demo_category", ch.get("group_title", "其他"))
            if cat == "央视" or cat == "CCTV":
                lite_channels.append(ch)
            else:
                if cat_counts.get(cat, 0) < 50:
                    lite_channels.append(ch)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
        
        # 生成精简版 M3U
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write("# 精简版 - 仅保留最稳定源，适合移动设备\n")
            f.write(f"# 共 {len(lite_channels)} 个频道（央视全部保留，其他分类限50个）\n")
            
            for ch in lite_channels:
                url = ch.get("urls", [ch.get("url")])[0]
                cat = ch.get("demo_category", ch.get("group_title", ""))
                f.write(f'#EXTINF:-1 group-title="{cat}",{ch["name"]}\n{url}\n')
        
        logger.info(f"✅ 精简版已生成: {path} (共 {len(lite_channels)} 个频道)")
