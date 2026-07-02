# ===================== 构建阶段 =====================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn \
    && find /usr/local/lib/python3.11 \
    \( -name "__pycache__" -o -name "*.pyc" -o -name "*.pyo" -o -name "*.dist-info" -o -name "*.egg-info" -o -name "tests" -o -name "docs" -o -name "examples" -o -name "test" \) \
    -exec rm -rf {} + || true

# ===================== 运行阶段 =====================
FROM python:3.11-slim-bookworm

WORKDIR /app

# 只装ffmpeg，ffprobe自带，删除大量系统冗余
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # 系统无用资源批量删除
    && rm -rf /usr/share/doc /usr/share/man /usr/share/locale /usr/share/info /usr/share/groff /usr/share/lintian \
    && rm -rf /var/cache/* /var/log/* /tmp/* \
    && rm -rf /usr/include /usr/lib/gcc /usr/lib/pkgconfig \
    && ffprobe -version

COPY --from=builder /usr/local /usr/local

COPY src/ ./src/
COPY demo.txt alias.txt blacklist.txt ./
COPY entrypoint.sh ./

RUN mkdir -p /app/data /app/output && chmod +x /app/entrypoint.sh

ENV AUTONOMOUS_MODE=true \
    FFMPEG_ENABLE=true \
    MAX_WORKERS=20 \
    TIMEOUT=8 \
    CACHE_HOURS=24 \
    CACHE_RAW_HOURS=48 \
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
