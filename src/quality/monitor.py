# src/quality/monitor.py
"""质量监控 - 持续检测源质量"""

import asyncio
import aiohttp
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.logger import logger
from src.speed_tester import probe_channel_advanced
from src.quality.models import QualityReport, QualityStatus


class QualityMonitor:
    """
    质量监控器
    
    监控指标:
    - 成功率: 最近N次测试的成功比例
    - 平均延迟: 最近N次的平均延迟
    - 失败趋势: 连续失败次数
    """
    
    CHECK_WINDOW = 10              # 最近10次测试
    CHECK_INTERVAL_HOURS = 24      # 每24小时检查一次
    LATENCY_WARN_THRESHOLD = 3000  # 延迟超过3秒告警
    LATENCY_CRITICAL_THRESHOLD = 5000  # 延迟超过5秒严重
    
    def __init__(self, stable_manager=None):
        from src.stable.manager import StableManager
        self.stable_manager = stable_manager or StableManager()
        self._history: Dict[str, deque] = {}  # channel_name -> deque
        self._last_check: Dict[str, datetime] = {}
    
    def _get_history(self, channel_name: str) -> deque:
        """获取频道历史记录"""
        if channel_name not in self._history:
            self._history[channel_name] = deque(maxlen=self.CHECK_WINDOW)
        return self._history[channel_name]
    
    async def check_channel(self, channel_name: str, url: str, session: aiohttp.ClientSession) -> tuple:
        """检查单个频道质量"""
        channel = {"name": channel_name, "url": url}
        _, latency, ok, _ = await probe_channel_advanced(session, channel)
        
        history = self._get_history(channel_name)
        history.append((datetime.now(), ok, latency))
        
        return ok, latency
    
    def get_quality_report(self, channel_name: str) -> QualityReport:
        """获取频道质量报告"""
        history = self._get_history(channel_name)
        if not history:
            return QualityReport(
                channel_name=channel_name,
                status=QualityStatus.UNKNOWN,
                success_rate=0,
                avg_latency=0,
                sample_count=0,
                last_check=datetime.now(),
                consecutive_fails=0
            )
        
        total = len(history)
        success_count = sum(1 for _, ok, _ in history if ok)
        success_rate = success_count / total if total > 0 else 0
        
        latencies = [lat for _, ok, lat in history if ok]
        avg_latency = sum(latencies) // len(latencies) if latencies else 9999
        
        # 计算连续失败次数
        consecutive_fails = 0
        for _, ok, _ in reversed(history):
            if not ok:
                consecutive_fails += 1
            else:
                break
        
        # 分析状态
        if consecutive_fails >= 3:
            status = QualityStatus.CRITICAL
        elif success_rate < 0.5 or avg_latency > self.LATENCY_CRITICAL_THRESHOLD:
            status = QualityStatus.CRITICAL
        elif success_rate < 0.8 or avg_latency > self.LATENCY_WARN_THRESHOLD:
            status = QualityStatus.WARNING
        else:
            status = QualityStatus.HEALTHY
        
        return QualityReport(
            channel_name=channel_name,
            status=status,
            success_rate=success_rate,
            avg_latency=avg_latency,
            sample_count=total,
            last_check=datetime.now(),
            consecutive_fails=consecutive_fails
        )
    
    def should_replace(self, channel_name: str) -> bool:
        """判断是否需要替换该频道"""
        report = self.get_quality_report(channel_name)
        
        # 从稳定管理器获取固定源信息
        src = self.stable_manager.stable_sources.get(channel_name)
        if src and src.is_fixed:
            return False
        
        return report.needs_replacement()
    
    async def check_all_active_sources(self, concurrency: int = 10) -> List[QualityReport]:
        """检查所有活跃源的质量"""
        active_sources = self.stable_manager.get_active_sources()
        if not active_sources:
            return []
        
        logger.info(f"🔍 检查 {len(active_sources)} 个活跃源的质量...")
        
        reports = []
        semaphore = asyncio.Semaphore(concurrency)
        
        async with aiohttp.ClientSession() as session:
            async def check_one(name, src):
                async with semaphore:
                    ok, latency = await self.check_channel(name, src.url, session)
                    if ok:
                        self.stable_manager.record_success(name)
                    else:
                        self.stable_manager.record_failure(name)
                    return self.get_quality_report(name)
            
            tasks = [check_one(name, src) for name, src in active_sources.items()]
            reports = await asyncio.gather(*tasks)
        
        # 统计
        healthy = sum(1 for r in reports if r.status == QualityStatus.HEALTHY)
        warning = sum(1 for r in reports if r.status == QualityStatus.WARNING)
        critical = sum(1 for r in reports if r.status == QualityStatus.CRITICAL)
        
        logger.info(f"📊 质量检查结果: 健康={healthy}, 警告={warning}, 严重={critical}")
        
        return reports
    
    def get_critical_sources(self) -> List[str]:
        """获取需要替换的源列表"""
        critical = []
        for name, src in self.stable_manager.stable_sources.items():
            if src.is_fixed:
                continue
            report = self.get_quality_report(name)
            if report.status == QualityStatus.CRITICAL:
                critical.append(name)
        return critical
