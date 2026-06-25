# src/gui/main_window.py
"""IPTV 智能管理 GUI 主窗口"""

import sys
import os
import asyncio
import threading
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.run import main as run_collector
from src.core.config import OUTPUT_DIR
from src.gui.widgets import LogTextEdit, ChannelTable, DashboardWidget
from src.gui.styles import DARK_STYLE


class IPTVMainWindow(QMainWindow):
    """IPTV 智能管理主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📡 IPTV 智能管理工具")
        self.setMinimumSize(1000, 700)
        self.setWindowIcon(QIcon("resources/icon.ico"))
        
        # 采集任务状态
        self.is_running = False
        self.collector_thread = None
        
        self.setup_ui()
        self.apply_style()
        self.load_status()
    
    def setup_ui(self):
        """初始化 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 菜单栏
        self.create_menu_bar()
        
        # 主布局
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧导航
        self.nav_list = QListWidget()
        self.nav_list.addItems(["📊 仪表盘", "📋 频道列表", "📌 固定源管理", "⚙️ 配置管理"])
        self.nav_list.setFixedWidth(150)
        self.nav_list.currentRowChanged.connect(self.switch_page)
        main_splitter.addWidget(self.nav_list)
        
        # 右侧内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(DashboardWidget(self))      # 仪表盘
        self.content_stack.addWidget(ChannelTable(self))         # 频道列表
        self.content_stack.addWidget(FixedSourceWidget(self))    # 固定源管理
        self.content_stack.addWidget(ConfigWidget(self))         # 配置管理
        main_splitter.addWidget(self.content_stack)
        
        layout.addWidget(main_splitter)
        
        # 底部控制栏
        self.create_bottom_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        open_action = QAction("📂 打开输出目录", self)
        open_action.triggered.connect(self.open_output_dir)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 操作菜单
        action_menu = menubar.addMenu("操作")
        start_action = QAction("▶ 启动采集", self)
        start_action.triggered.connect(self.start_collection)
        action_menu.addAction(start_action)
        stop_action = QAction("⏹ 停止采集", self)
        stop_action.triggered.connect(self.stop_collection)
        action_menu.addAction(stop_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_bottom_bar(self):
        """创建底部控制栏"""
        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(80)
        layout = QHBoxLayout(bottom_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 控制按钮
        self.start_btn = QPushButton("▶ 启动采集")
        self.start_btn.clicked.connect(self.start_collection)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_collection)
        layout.addWidget(self.stop_btn)
        
        layout.addSpacing(20)
        
        # 打开目录按钮
        open_dir_btn = QPushButton("📂 打开输出目录")
        open_dir_btn.clicked.connect(self.open_output_dir)
        layout.addWidget(open_dir_btn)
        
        layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # 日志文本框
        self.log_text = LogTextEdit(self)
        self.log_text.setFixedHeight(120)
        
        # 添加到主布局
        main_layout = self.centralWidget().layout()
        main_layout.addWidget(bottom_widget)
        main_layout.addWidget(self.log_text)
    
    def switch_page(self, index):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
    
    def start_collection(self):
        """启动采集任务"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("采集运行中...")
        self.log_text.clear()
        self.log_text.append_log("🚀 开始采集任务...")
        
        # 在新线程中运行采集
        self.collector_thread = threading.Thread(target=self._run_collector, daemon=True)
        self.collector_thread.start()
    
    def _run_collector(self):
        """在线程中运行采集"""
        try:
            # 重定向日志到 GUI
            from src.utils.logger_handler import gui_log_handler
            gui_log_handler.set_callback(self.log_text.append_log)
            
            # 运行采集
            asyncio.run(run_collector())
            
            # 采集完成
            self.log_text.append_log("✅ 采集任务完成！")
            self.load_status()
            
        except Exception as e:
            self.log_text.append_log(f"❌ 采集失败: {e}")
        
        finally:
            # 恢复状态
            QMetaObject.invokeMethod(self, "_on_collection_finished", Qt.QueuedConnection)
    
    @Slot()
    def _on_collection_finished(self):
        """采集完成回调（在主线程执行）"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("就绪")
    
    def stop_collection(self):
        """停止采集"""
        # 由于 asyncio 无法强制停止，这里只是标记
        self.log_text.append_log("⏹ 正在停止采集...")
        self.is_running = False
        self.stop_btn.setEnabled(False)
        self.status_label.setText("停止中...")
    
    def load_status(self):
        """加载状态信息"""
        # 刷新仪表盘
        dashboard = self.content_stack.widget(0)
        if dashboard:
            dashboard.refresh()
    
    def open_output_dir(self):
        """打开输出目录"""
        output_path = Path(OUTPUT_DIR)
        if output_path.exists():
            os.startfile(str(output_path))
        else:
            QMessageBox.warning(self, "提示", f"输出目录不存在: {output_path}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 IPTV 智能管理工具",
            "📡 IPTV 智能管理工具 v1.0\n\n"
            "基于 PySide6 开发的 IPTV 直播源管理工具\n\n"
            "功能：\n"
            "  • 多源自动采集\n"
            "  • HTTP 测速 + ffmpeg 深度验证\n"
            "  • 智能分类（央视/卫视/地方/港澳台）\n"
            "  • 固定源管理\n"
            "  • 质量趋势监控\n\n"
            "© 2026 IPTV Collector"
        )
    
    def apply_style(self):
        """应用暗色主题样式"""
        self.setStyleSheet(DARK_STYLE)
