# src/main.py
"""IPTV 智能管理 GUI 工具 - 程序入口"""

import sys
import os
import traceback
from pathlib import Path

# 确保当前目录在 sys.path 中（打包后会被解压到临时目录，但我们需要当前 exe 所在目录）
# 如果运行的是打包后的 exe，sys.executable 是 exe 路径，其父目录是程序所在目录
base_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / 'src'))  # 确保 src 可导入

def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from src.gui.main_window import IPTVMainWindow
        from src.utils.logger_handler import setup_gui_logging

        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        app.setApplicationName("IPTV 智能管理工具")
        app.setOrganizationName("IPTVCollector")
        
        setup_gui_logging()
        
        window = IPTVMainWindow()
        window.show()
        
        sys.exit(app.exec())
    
    except Exception as e:
        error_msg = traceback.format_exc()
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except:
            pass
        print("=" * 60)
        print("程序启动失败！")
        print("错误信息已写入 error.log")
        print("=" * 60)
        print(error_msg)
        input("按 Enter 键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()
