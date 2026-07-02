# Dockerfile
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# 安装编译依赖（仅构建阶段）
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 使用国内镜像源加速（可选）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# ===== 运行时镜像 =====
FROM python:3.11-slim-bookworm

WORKDIR /app

# 安装运行时依赖（ffmpeg 用于验证）
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    ffprobe -version

# 复制已安装的 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目文件（排除 gui/ 等无需在容器内运行的文件）
COPY src/ ./src/
COPY demo.txt alias.txt blacklist.txt ./
COPY entrypoint.sh ./

# 创建数据目录
RUN mkdir -p /app/data /app/output

# 设置默认环境变量（可被 docker-compose 覆盖）
ENV AUTONOMOUS_MODE=true \
    FFMPEG_ENABLE=true \
    MAX_WORKERS=20 \
    TIMEOUT=8 \
    CACHE_HOURS=24 \
    CACHE_RAW_HOURS=48 \
    CACHE_SPEED_HOURS=24 \
    ENABLE_INCREMENTAL_FETCH=true \
    ENABLE_DEMO_FILTER=true \
    ENABLE_ALIAS=true \
    ENABLE_BLACKLIST=true \
    DATABASE_ENABLE=true \
    RUN_MODE=schedule \
    SCHEDULE_INTERVAL=21600 \
    WEB_SERVER_PORT=8080 \
    WEB_SERVER_HOST=0.0.0.0 \
    ENABLE_JSON_OUTPUT=true \
    ENABLE_LITE_VERSION=false \
    ENABLE_EPG_OUTPUT=false \
    HTTP_TIMEOUT=8 \
    SLOW_SPEED_THRESHOLD=3000 \
    MAX_RETRY_BEFORE_BLACKLIST=2 \
    PREDICT_THRESHOLD=0.6 \
    HEALTH_HISTORY_DAYS=30

EXPOSE 8080

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
