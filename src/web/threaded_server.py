# src/web/threaded_server.py
"""后台 Flask 服务器（可在线程中运行）"""

from src.web.app import create_app


def run_server_in_thread(port: int):
    """在独立线程中运行 Flask 服务器"""
    app = create_app()
    # 禁用调试日志，避免干扰 GUI
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
