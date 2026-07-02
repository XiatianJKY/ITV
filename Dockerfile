# Dockerfile
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# 更换为国内镜像源（阿里云）
RUN echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装编译依赖（gcc）
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# 运行时镜像
FROM python:3.11-slim-bookworm

WORKDIR /app

# 同样使用阿里云镜像源
RUN echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装 ffmpeg curl
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && ffprobe -version

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN mkdir -p /app/data /app/output

EXPOSE 8080

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
