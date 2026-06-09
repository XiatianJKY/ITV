# IPTV 智能整理平台 Docker 部署指南

本指南帮助你快速在任意支持 Docker 的 Linux 设备（x86_64 / ARM64）上部署 IPTV 采集服务。  
容器内置 HTTP 文件服务器，采集完成后可直接通过 `http://设备IP:端口/tv.m3u` 或 `/tv.txt` 获取播放列表，无需额外配置 Nginx。

---

## 一、前提条件

- 已安装 **Docker** 和 **Docker Compose**（或 Docker Engine 24+ 内置 Compose v2）
- 开放目标端口（如 `8080`）用于访问播放列表
- 确保设备有稳定的网络连接（用于拉取 IPTV 源）

---

## 二、部署步骤

### 1. 下载项目文件

确保以下完整项目结构存在于设备上（可直接克隆或下载压缩包解压）：
iptv-collector/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example
├── requirements.txt
├── alias.txt
├── blacklist.txt
├── demo.txt
├── src/
│ ├── init.py
│ ├── alias_matcher.py
│ ├── blacklist_filter.py
│ ├── classifier.py
│ ├── config.py
│ ├── database.py
│ ├── demo_filter.py
│ ├── fetcher.py
│ ├── ffmpeg_validator.py
│ ├── generator.py
│ ├── ip_resolver.py
│ ├── logger.py
│ ├── merger.py
│ ├── parser.py
│ ├── run.py
│ ├── server.py
│ ├── speed_tester.py
│ └── update_ipdb.py
├── data/ # 自动生成（缓存数据库）
└── output/ # 自动生成（播放列表）

text

### 2. 进入项目目录

```bash
cd iptv-collector
3. 配置环境变量（可选）
复制示例环境变量文件：

bash
cp .env.example .env
根据需要修改 .env 中的参数（详见下文「配置说明」）。
若不创建 .env 文件，所有参数将使用默认值。

4. 构建并启动容器
使用 Docker Compose 一键构建并启动：

bash
docker-compose up -d --build
-d 后台运行

--build 强制重新构建镜像（首次必须）

5. 查看运行日志
bash
docker logs -f iptv-collector
当看到类似 HTTP 文件服务器已启动 和 采集任务完成 的日志时，表示服务正常。

三、访问播放列表
容器启动后，会同时运行：

采集任务（一次性或定时）

HTTP 服务器（端口 8000 容器内，已映射到主机 8080）

使用设备 IP + 映射端口访问：

bash
# 查看设备 IP（示例）
ip addr show

# 浏览器或播放器中打开：
http://192.168.1.100:8080/tv.m3u     # M3U 格式
http://192.168.1.100:8080/tv.txt     # TXT 格式（频道名,URL）
端口映射在 docker-compose.yml 中定义为 "8080:8000"，可修改左侧主机端口。

四、配置说明
运行模式
环境变量	说明	默认值
RUN_MODE	once：执行一次后退出；schedule：定时执行	once
SCHEDULE_INTERVAL	定时模式下的采集间隔（秒）	21600（6小时）
性能调优
变量	说明	默认值
MAX_WORKERS	并发探测频道数	10
TIMEOUT	HTTP 探测超时（秒）	10
FFMPEG_ENABLE	是否启用 ffmpeg 深度验证	true
ENABLE_RETRY	拉取源失败时重试	true
缓存与输出
变量	说明	默认值
CACHE_SPEED_HOURS	测速结果缓存时长（小时）	24
CACHE_RAW_HOURS	原始源内容缓存时长（小时）	24
MAX_SOURCES_PER_CHANNEL	每个频道保留的最大源数量	5
DEMO_MATCH_MODE	demo 匹配模式（contains / exact）	contains
功能开关
变量	说明	默认值
ENABLE_DEMO_FILTER	按 demo.txt 过滤频道	true
ENABLE_ALIAS	启用别名标准化	true
ENABLE_BLACKLIST	启用 URL 黑名单	true
DATABASE_ENABLE	启用 SQLite 缓存	true
ENABLE_IP_RESOLVE	启用 IP 归属地解析	true
ENABLE_REGION_FILTER	启用地域筛选（需 IP 解析）	false
Web 服务器
变量	说明	默认值
WEB_SERVER_HOST	HTTP 服务器监听地址	0.0.0.0
WEB_SERVER_PORT	HTTP 服务器端口（容器内）	8000
修改 WEB_SERVER_PORT 后需同步修改 docker-compose.yml 中的端口映射。

五、自定义数据卷
docker-compose.yml 已挂载以下目录：

./data → 容器 /app/data：SQLite 缓存数据库，持久化后避免重复拉取源

./output → 容器 /app/output：生成的播放列表和日志

./alias.txt、./blacklist.txt、./demo.txt 只读挂载，可随时修改而无需重建镜像

六、故障排查
1. 容器启动后立即退出
查看详细日志：

bash
docker logs iptv-collector
常见原因：

缺少 alias.txt、blacklist.txt、demo.txt（项目根目录必须存在）

端口冲突（修改 docker-compose.yml 中的主机端口）

2. 播放列表无法访问
确认容器运行状态：docker ps

确认防火墙已放行映射端口（如 8080）

尝试在容器内部测试：docker exec -it iptv-collector curl http://localhost:8000/tv.m3u

3. ffmpeg 深度验证失败
日志中出现 ffprobe 不可用：请确认 Dockerfile 中已安装 ffmpeg（本项目已集成）

若宿主机是 ARM 架构，基础镜像会自动拉取 arm64 版本的 ffmpeg

4. IP 数据库下载失败
容器启动时会尝试下载 qqwry.dat，若网络问题导致失败，可使用已有文件或手动放入项目根目录。
不影响核心采集功能，仅影响 IP 归属地解析。

七、多架构支持
基础镜像 python:3.10-slim-bookworm 官方支持 linux/amd64 和 linux/arm64

Dockerfile 中通过 apt-get 安装的 ffmpeg 也会自动匹配架构

如需构建多架构镜像并推送到仓库：

bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t yourname/iptv-collector:latest --push .
八、播放器使用示例
播放器	操作
VLC	媒体 → 打开网络串流 → 输入 http://设备IP:8080/tv.m3u
PotPlayer	右键 → 打开链接 → 粘贴 M3U 地址
IINA（macOS）	文件 → 打开 URL → 输入地址
Kodi	添加视频源 → 选择「M3U 播放列表」→ 填入 URL
Tivimate（Android TV）	添加播放列表 → 远程列表 → 输入地址
九、卸载与清理
停止并删除容器：

bash
docker-compose down
删除持久化数据（缓存和输出）：

bash
rm -rf data output
删除镜像（可选）：

bash
docker rmi iptv-collector
十、许可证与免责声明
本项目仅供个人学习和研究使用，请勿用于商业或非法传播。
所有节目源均来自互联网公开链接，项目本身不存储、不修改任何媒体内容。
使用者须遵守当地法律法规，因违规使用产生的责任由使用者自行承担。

祝你使用愉快！ 🎬
如有问题，欢迎提交 Issue。
