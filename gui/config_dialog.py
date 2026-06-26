# gui/config_dialog.py
import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                             QLineEdit, QCheckBox, QSpinBox, QPushButton, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt
import configparser

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置")
        self.setMinimumWidth(400)
        self.config = configparser.ConfigParser()
        self.config_file = os.path.join(os.path.dirname(sys.executable), "config.ini")
        self.load_config()
        self.init_ui()

    def load_config(self):
        """加载配置文件，如果不存在则使用默认值"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # 设置默认值
            self.config['DEFAULT'] = {
                'MAX_WORKERS': '20',
                'TIMEOUT': '8',
                'FFMPEG_ENABLE': 'true',
                'ENABLE_DEMO_FILTER': 'true',
                'ENABLE_ALIAS': 'true',
                'ENABLE_BLACKLIST': 'true'
            }

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # 创建控件
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 100)
        self.max_workers_spin.setValue(int(self.config.get('DEFAULT', 'MAX_WORKERS', fallback='20')))

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(int(self.config.get('DEFAULT', 'TIMEOUT', fallback='8')))

        self.ffmpeg_check = QCheckBox()
        self.ffmpeg_check.setChecked(self.config.getboolean('DEFAULT', 'FFMPEG_ENABLE', fallback=True))

        self.demo_check = QCheckBox()
        self.demo_check.setChecked(self.config.getboolean('DEFAULT', 'ENABLE_DEMO_FILTER', fallback=True))

        self.alias_check = QCheckBox()
        self.alias_check.setChecked(self.config.getboolean('DEFAULT', 'ENABLE_ALIAS', fallback=True))

        self.blacklist_check = QCheckBox()
        self.blacklist_check.setChecked(self.config.getboolean('DEFAULT', 'ENABLE_BLACKLIST', fallback=True))

        form_layout.addRow("最大并发数:", self.max_workers_spin)
        form_layout.addRow("超时时间(秒):", self.timeout_spin)
        form_layout.addRow("启用 FFmpeg 验证:", self.ffmpeg_check)
        form_layout.addRow("启用 Demo 筛选:", self.demo_check)
        form_layout.addRow("启用别名标准化:", self.alias_check)
        form_layout.addRow("启用黑名单过滤:", self.blacklist_check)

        layout.addLayout(form_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def save_config(self):
        """保存配置到 config.ini"""
        try:
            self.config['DEFAULT']['MAX_WORKERS'] = str(self.max_workers_spin.value())
            self.config['DEFAULT']['TIMEOUT'] = str(self.timeout_spin.value())
            self.config['DEFAULT']['FFMPEG_ENABLE'] = str(self.ffmpeg_check.isChecked()).lower()
            self.config['DEFAULT']['ENABLE_DEMO_FILTER'] = str(self.demo_check.isChecked()).lower()
            self.config['DEFAULT']['ENABLE_ALIAS'] = str(self.alias_check.isChecked()).lower()
            self.config['DEFAULT']['ENABLE_BLACKLIST'] = str(self.blacklist_check.isChecked()).lower()

            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            QMessageBox.information(self, "成功", "配置已保存")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
