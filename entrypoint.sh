#!/bin/bash
set -e

echo "=========================================="
echo "IPTV 智能整理平台 Docker 容器启动"
echo "检测架构: $(uname -m)"
echo "=========================================="

mkdir -p /app/data /app/output
cd /app

# 启动 Web 管理界面（Flask）
echo "启动 Web 管理界面..."
python -m src.server 2>&1 | tee -a /app/output/web.log &
WEB_PID=$!

sleep 3
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "❌ Web 服务启动失败，查看 /app/output/web.log"
    cat /app/output/web.log
    exit 1
fi
echo "✅ Web 管理界面已启动（PID: $WEB_PID）"

# 采集任务
RUN_MODE=${RUN_MODE:-once}
INTERVAL=${SCHEDULE_INTERVAL:-21600}

run_collector() {
    if [ "$RUN_MODE" = "once" ]; then
        echo "执行一次性采集任务..."
        python -m src.run
        echo "✅ 采集完成"
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
        echo "未知运行模式: $RUN_MODE"
        exit 1
    fi
}

run_collector
