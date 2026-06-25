# src/gui/__init__.py
"""GUI 模块"""

from src.gui.main_window import IPTVMainWindow
from src.gui.widgets import LogTextEdit, ChannelTable, DashboardWidget

__all__ = ["IPTVMainWindow", "LogTextEdit", "ChannelTable", "DashboardWidget"]
