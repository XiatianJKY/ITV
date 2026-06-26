import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .worker import CollectionWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker = None

    def initUI(self):
        # ... 创建界面控件，如按钮、文本框等 ...
        self.start_btn = QPushButton("开始采集", self)
        self.start_btn.clicked.connect(self.start_collection)

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)

        # ... 布局代码 ...

    def start_collection(self):
        # 1. 禁用按钮，防止重复点击
        self.start_btn.setEnabled(False)
        self.log_text.append("🚀 开始采集任务...")

        # 2. 创建并启动后台工作线程
        self.worker = CollectionWorker()
        # 连接信号，将日志输出到界面
        self.worker.log_signal.connect(self.append_log)
        # 线程结束后，重新启用按钮
        self.worker.finished.connect(self.on_collection_finished)
        self.worker.start()

    def append_log(self, message):
        # 将日志追加到文本框
        self.log_text.append(message)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def on_collection_finished(self):
        self.start_btn.setEnabled(True)
        self.log_text.append("🏁 采集任务结束")
