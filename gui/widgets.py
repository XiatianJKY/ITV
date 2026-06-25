# src/gui/widgets.py
"""GUI 自定义控件"""

import json
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from src.core.config import OUTPUT_DIR
from src.core.stable.manager import StableManager
from src.config import OUTPUT_DIR
from src.stable.manager import StableManager
from src.source_pool.discoverer import SourceDiscoverer
from src.candidate.observer import CandidateObserver

class LogTextEdit(QTextEdit):
    """日志输出控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
    
    def append_log(self, text: str):
        """追加日志（线程安全）"""
        QMetaObject.invokeMethod(self, "_append", Qt.QueuedConnection, Q_ARG(str, text))
    
    @Slot(str)
    def _append(self, text: str):
        """实际追加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append(f"[{timestamp}] {text}")
        # 自动滚动到底部
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class DashboardWidget(QWidget):
    """仪表盘控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        layout = QVBoxLayout(self)
        
        # 统计卡片
        self.card_layout = QGridLayout()
        self.card_layout.setSpacing(15)
        layout.addLayout(self.card_layout)
        
        # 创建四个统计卡片
        self.stats_cards = {}
        stats = [
            ("稳定源", "stable_count", "#0d6efd"),
            ("固定源", "fixed_count", "#198754"),
            ("源池总量", "pool_total", "#ffc107"),
            ("候选观察中", "candidate_observing", "#6f42c1"),
        ]
        for i, (label, key, color) in enumerate(stats):
            card = self.create_stat_card(label, key, color)
            self.card_layout.addWidget(card, i // 2, i % 2)
            self.stats_cards[key] = card
        
        # 系统信息
        info_group = QGroupBox("系统信息")
        info_layout = QVBoxLayout(info_group)
        self.last_run_label = QLabel("最后运行时间: 加载中...")
        self.status_label = QLabel("系统状态: 运行中")
        info_layout.addWidget(self.last_run_label)
        info_layout.addWidget(self.status_label)
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        # 定时刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(10000)  # 每10秒刷新
    
    def create_stat_card(self, label: str, key: str, color: str) -> QWidget:
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #2b3035;
                border: 1px solid #3d444b;
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        layout = QVBoxLayout(card)
        
        title = QLabel(label)
        title.setStyleSheet("color: #adb5bd; font-size: 12px;")
        layout.addWidget(title)
        
        value = QLabel("--")
        value.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        value.setObjectName(key)
        layout.addWidget(value)
        
        return card
    
    def refresh(self):
        """刷新数据"""
        try:
            from src.core.stable.manager import StableManager
            from src.core.source_pool.discoverer import SourceDiscoverer
            from src.core.candidate.observer import CandidateObserver
            
            stable_mgr = StableManager()
            stable_sources = stable_mgr.get_active_sources()
            fixed_count = sum(1 for s in stable_mgr.stable_sources.values() if s.is_fixed)
            
            discoverer = SourceDiscoverer()
            pool_stats = discoverer.get_statistics()
            
            observer = CandidateObserver()
            candidate_stats = observer.get_statistics()
            
            # 更新卡片
            self.findChild(QLabel, "stable_count").setText(str(len(stable_sources)))
            self.findChild(QLabel, "fixed_count").setText(str(fixed_count))
            self.findChild(QLabel, "pool_total").setText(str(pool_stats.get('total', 0)))
            self.findChild(QLabel, "candidate_observing").setText(str(candidate_stats.get('observing', 0)))
            
            # 更新系统信息
            stats_file = OUTPUT_DIR / "stats.json"
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_run_label.setText(f"最后运行时间: {data.get('timestamp', '未知')}")
            
        except Exception as e:
            pass


class ChannelTable(QWidget):
    """频道列表控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 搜索和筛选
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索频道...")
        self.search_input.textChanged.connect(self.load_channels)
        search_layout.addWidget(self.search_input)
        
        self.category_filter = QComboBox()
        self.category_filter.addItems(["全部分类", "央视", "卫视", "地方", "港澳台", "其他"])
        self.category_filter.currentTextChanged.connect(self.load_channels)
        search_layout.addWidget(self.category_filter)
        
        layout.addLayout(search_layout)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["频道名", "分类", "延迟(ms)", "固定", "操作"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # 定时刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_channels)
        self.timer.start(30000)  # 每30秒刷新
        
        self.load_channels()
    
    def load_channels(self):
        """加载频道列表"""
        try:
            from src.core.stable.manager import StableManager
            
            search = self.search_input.text().strip().lower()
            category = self.category_filter.currentText()
            
            stable_mgr = StableManager()
            sources = stable_mgr.get_active_sources()
            
            self.table.setRowCount(0)
            row = 0
            
            for name, src in sources.items():
                if not src.url:
                    continue
                if search and search not in name.lower():
                    continue
                
                # 判断分类
                cat = self._get_category(name)
                if category != "全部分类" and cat != category:
                    continue
                
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem(cat))
                self.table.setItem(row, 2, QTableWidgetItem(str(src.latency) if src.latency else "--"))
                self.table.setItem(row, 3, QTableWidgetItem("固定" if src.is_fixed else "普通"))
                
                row += 1
            
        except Exception as e:
            pass
    
    def _get_category(self, name: str) -> str:
        """获取频道分类"""
        if name.startswith("CCTV") or "央视" in name:
            return "央视"
        if "卫视" in name:
            return "卫视"
        if any(kw in name for kw in ["港", "澳", "台", "凤凰", "翡翠", "明珠", "TVB"]):
            return "港澳台"
        if "频道" in name:
            return "地方"
        return "其他"


class FixedSourceWidget(QWidget):
    """固定源管理控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 添加表单
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("频道名 (如 CCTV-1)")
        form_layout.addWidget(self.name_input)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URL")
        form_layout.addWidget(self.url_input)
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_fixed_source)
        form_layout.addWidget(add_btn)
        
        layout.addLayout(form_layout)
        
        # 消息提示
        self.message_label = QLabel()
        self.message_label.setStyleSheet("color: #ffc107;")
        layout.addWidget(self.message_label)
        
        # 列表
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["频道名", "URL", "操作"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        self.load_fixed_sources()
    
    def add_fixed_source(self):
        """添加固定源"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name or not url:
            self.message_label.setText("⚠️ 请填写完整信息")
            return
        
        try:
            from src.core.stable.manager import StableManager
            stable_mgr = StableManager()
            if stable_mgr.set_fixed_source(name, url):
                self.message_label.setText(f"✅ 已添加固定源: {name}")
                self.name_input.clear()
                self.url_input.clear()
                self.load_fixed_sources()
            else:
                self.message_label.setText("❌ 添加失败")
        except Exception as e:
            self.message_label.setText(f"❌ 错误: {e}")
    
    def load_fixed_sources(self):
        """加载固定源列表"""
        try:
            from src.core.stable.manager import StableManager
            
            stable_mgr = StableManager()
            fixed = {name: src.url for name, src in stable_mgr.stable_sources.items() if src.is_fixed}
            
            self.table.setRowCount(0)
            row = 0
            
            for name, url in fixed.items():
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem(url))
                
                # 删除按钮
                del_btn = QPushButton("删除")
                del_btn.clicked.connect(lambda checked, n=name: self.delete_fixed_source(n))
                self.table.setCellWidget(row, 2, del_btn)
                
                row += 1
                
        except Exception as e:
            pass
    
    def delete_fixed_source(self, name: str):
        """删除固定源"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除固定源 {name} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                from src.core.stable.manager import StableManager
                stable_mgr = StableManager()
                if name in stable_mgr.stable_sources:
                    stable_mgr.stable_sources[name].is_fixed = False
                    stable_mgr._save()
                    self.message_label.setText(f"✅ 已移除固定源: {name}")
                    self.load_fixed_sources()
            except Exception as e:
                self.message_label.setText(f"❌ 错误: {e}")


class ConfigWidget(QWidget):
    """配置管理控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        group = QGroupBox("系统配置")
        form_layout = QFormLayout(group)
        
        self.max_workers = QSpinBox()
        self.max_workers.setRange(1, 100)
        self.max_workers.setValue(20)
        form_layout.addRow("最大并发数:", self.max_workers)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 60)
        self.timeout.setValue(8)
        form_layout.addRow("超时时间 (秒):", self.timeout)
        
        self.max_sources = QSpinBox()
        self.max_sources.setRange(1, 10)
        self.max_sources.setValue(3)
        form_layout.addRow("每个频道保留源数:", self.max_sources)
        
        self.demo_mode = QComboBox()
        self.demo_mode.addItems(["contains", "exact"])
        form_layout.addRow("Demo匹配模式:", self.demo_mode)
        
        self.ffmpeg_enable = QCheckBox("启用 ffmpeg 深度验证")
        self.ffmpeg_enable.setChecked(True)
        form_layout.addRow("", self.ffmpeg_enable)
        
        layout.addWidget(group)
        
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)
        
        self.message_label = QLabel()
        self.message_label.setStyleSheet("color: #ffc107;")
        layout.addWidget(self.message_label)
        
        layout.addStretch()
        
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        try:
            from src.core.config import (
                MAX_WORKERS, TIMEOUT, FFMPEG_ENABLE,
                MAX_SOURCES_PER_CHANNEL, DEMO_MATCH_MODE
            )
            self.max_workers.setValue(MAX_WORKERS)
            self.timeout.setValue(TIMEOUT)
            self.max_sources.setValue(MAX_SOURCES_PER_CHANNEL)
            self.demo_mode.setCurrentText(DEMO_MATCH_MODE)
            self.ffmpeg_enable.setChecked(FFMPEG_ENABLE)
        except Exception:
            pass
    
    def save_config(self):
        """保存配置"""
        try:
            import os
            env_path = Path(".env")
            
            config = {
                "MAX_WORKERS": self.max_workers.value(),
                "TIMEOUT": self.timeout.value(),
                "MAX_SOURCES_PER_CHANNEL": self.max_sources.value(),
                "DEMO_MATCH_MODE": self.demo_mode.currentText(),
                "FFMPEG_ENABLE": str(self.ffmpeg_enable.isChecked()).lower(),
            }
            
            # 读取现有 .env 文件
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # 更新配置
            updated_keys = set()
            new_lines = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith('#'):
                    key = line_stripped.split('=')[0].strip()
                    if key in config:
                        new_lines.append(f"{key}={config[key]}\n")
                        updated_keys.add(key)
                        continue
                new_lines.append(line)
            
            # 添加未更新的键
            for key, value in config.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}\n")
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            self.message_label.setText("✅ 配置已保存，请重启工具生效")
            
        except Exception as e:
            self.message_label.setText(f"❌ 保存失败: {e}")
