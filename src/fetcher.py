# src/fetcher.py
# 在文件顶部添加一个针对特定源的请求头映射

import aiohttp
import asyncio
from src.config import HEADERS, TIMEOUT, RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_MAX_WAIT, ENABLE_RETRY
from src.database import get_db_cache
from src.logger import logger

# 针对港澳台日源的专用请求头（模拟浏览器）
HMTJ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# 判断是否为港澳台日源
def is_hmtj_url(url: str) -> bool:
    return any(domain in url for domain in [
        "live.hacks.tools",
        "tv/ipv4/categories/hong_kong",
        "tv/ipv4/categories/macau",
        "tv/ipv4/categories/taiwan",
        "iptv/languages/jpn"
    ])

async def fetch_url_with_metadata(session: aiohttp.ClientSession, url: str, db):
    # 为港澳台日源使用专用请求头
    headers = HMTJ_HEADERS if is_hmtj_url(url) else HEADERS

    # 尝试从缓存获取
    cached_content = await db.get_raw_source(url) if db else None
    if cached_content:
        logger.debug(f"✅ 使用缓存: {url}")
        return cached_content

    logger.info(f"🔄 拉取: {url}")
    attempt = 0
    while True:
        attempt += 1
        try:
            async with session.get(url, timeout=TIMEOUT, headers=headers) as resp:
                if resp.status != 200:
                    raise FetchError(f"HTTP {resp.status}")
                content = await resp.text()
                if db:
                    await db.set_raw_source(url, content)
                return content
        except Exception as e:
            if not ENABLE_RETRY or attempt >= RETRY_MAX_ATTEMPTS:
                raise FetchError(str(e))
            wait_time = min(RETRY_BACKOFF_FACTOR ** (attempt - 1), RETRY_MAX_WAIT)
            logger.warning(f"  重试 {url} ({attempt}/{RETRY_MAX_ATTEMPTS})，等待 {wait_time}s")
            await asyncio.sleep(wait_time)

# 其他函数（fetch_all_sources_incremental 等）保持不变
