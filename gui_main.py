#!/usr/bin/env python3
# gui_main.py
"""IPTV 管理桌面应用 (PyQt5)"""

import os
import sys
import threading
import random
from pathlib import Path

# ========== 设置环境变量（启用自治模式） ==========
os.environ["AUTONOMOUS_MODE"] = "true"
os.environ["ENABLE_DEMO_FILTER"] = "true"
os.environ["ENABLE_ALIAS"] = "true"
os.environ["ENABLE_BLACKLIST"] = "true"
os.environ["DATABASE_ENABLE"] = "true"
os.environ["FFMPEG_ENABLE"] = "true"
os.environ["MAX_WORKERS"] = "20"
os.environ["TIMEOUT"] = "8"

# ========== 切换工作目录到 exe 所在目录 ==========
if getattr(sys, 'frozen', False):
    # 打包环境，exe 所在路径
    base_dir = Path(sys.executable).parent
    os.chdir(base_dir)
    print(f"📁 工作目录已切换至: {base_dir}")
else:
    base_dir = Path(__file__).parent
    os.chdir(base_dir)
    print(f"📁 开发环境工作目录: {base_dir}")

# 添加项目根目录到 sys.path
sys.path.insert(0, str(base_dir))

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings

from src.web.threaded_server import run_server_in_thread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV 智能管理")
        self.setGeometry(100, 100, 1200, 800)

        # 启动后台 Flask 服务器（随机端口）
        self.port = random.randint(49152, 65535)
        self.server_thread = threading.Thread(
            target=run_server_in_thread,
            args=(self.port,),
            daemon=True
        )
        self.server_thread.start()

        # 等待服务器启动后加载页面
        QTimer.singleShot(2000, self.load_web)

    def load_web(self):
        # 创建 Web 视图
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(f"http://127.0.0.1:{self.port}/"))
        self.setCentralWidget(self.browser)

        # 检查连接
        self.browser.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if not ok:
            QMessageBox.warning(
                self,
                "连接失败",
                "无法连接到本地服务器，请检查防火墙或重启应用。"
            )


def main():
    app = QApplication(sys.argv)
    # 设置 Web 引擎参数
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.NoCache)
    settings = QWebEngineSettings.defaultSettings()
    settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
    settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
