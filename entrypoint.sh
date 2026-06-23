#!/bin/bash
set -e

echo "=========================================="
echo "IPTV 智能整理平台 Docker 容器启动"
echo "检测架构: $(uname -m)"
echo "=========================================="

mkdir -p /app/data /app/output
cd /app

# 可选：更新 IP 数据库（不影响核心功能）
if [ ! -f /app/qqwry.dat ] || [ "$(stat -c %s /app/qqwry.dat 2>/dev/null || echo 0)" -lt 1048576 ]; then
    echo "正在更新 IP 数据库..."
    python -m src.update_ipdb 2>/dev/null || echo "⚠️ IP 数据库更新失败，将使用已有文件（如有）"
fi

# ========== 启动 Web 管理界面（Flask） ==========
echo "启动 Web 管理界面（Flask）..."
# 检查 Flask 是否已安装
if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️ Flask 未安装，正在尝试安装..."
    pip install Flask flask-cors 2>/dev/null || echo "⚠️ Flask 安装失败，请手动安装"
fi

# 启动 Flask 应用，日志输出到 /app/output/web.log
python -m src.server >> /app/output/web.log 2>&1 &
WEB_PID=$!
echo "Web 服务进程 PID: $WEB_PID"

sleep 3
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "❌ Web 服务启动失败，查看 /app/output/web.log"
    cat /app/output/web.log
    exit 1
fi
echo "✅ Web 管理界面已启动（访问 http://localhost:${WEB_SERVER_PORT:-8080}）"

# ========== 采集任务 ==========
RUN_MODE=${RUN_MODE:-once}
INTERVAL=${SCHEDULE_INTERVAL:-21600}

run_collector() {
    if [ "$RUN_MODE" = "once" ]; then
        echo "执行一次性采集任务..."
        python -m src.run
        echo "✅ 一次性采集完成，Web 服务继续运行"
        wait $WEB_PID
    elif [ "$RUN_MODE" = "schedule" ]; then
        echo "启动定时模式，每 ${INTERVAL} 秒执行一次"
        while true; do
            echo "$(date): 开始采集任务..."
            python -m src.run
            echo "$(date): 采集完成，等待 ${INTERVAL} 秒后继续..."
            sleep $INTERVAL
        done
    else
        echo "未知运行模式: $RUN_MODE，请设置为 once 或 schedule"
        exit 1
    fi
}

run_collector
