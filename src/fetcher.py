# src/fetcher.py
# 源拉取模块，支持源变更检测

import asyncio
import aiohttp
import hashlib
from src.config import HEADERS, TIMEOUT, RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_MAX_WAIT, ENABLE_RETRY
from src.database import get_db_cache

class FetchError(Exception):
    pass

async def fetch_url_with_etag(session: aiohttp.ClientSession, url: str) -> tuple:
    """拉取 URL 内容，返回 (content, etag, last_modified)"""
    attempt = 0
    while True:
        attempt += 1
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as resp:
                if resp.status != 200:
                    raise FetchError(f"HTTP {resp.status}")
                content = await resp.text()
                etag = resp.headers.get("ETag", "")
                last_modified = resp.headers.get("Last-Modified", "")
                return content, etag, last_modified
        except Exception as e:
            if not ENABLE_RETRY or attempt >= RETRY_MAX_ATTEMPTS:
                raise FetchError(str(e))
            wait_time = min(RETRY_BACKOFF_FACTOR ** (attempt - 1), RETRY_MAX_WAIT)
            print(f"  重试 {url} ({attempt}/{RETRY_MAX_ATTEMPTS})，等待 {wait_time}s")
            await asyncio.sleep(wait_time)

def compute_content_hash(content: str) -> str:
    """计算内容的 MD5 哈希"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

async def check_sources_changed(sources: list) -> tuple:
    """
    检查源是否有变化。
    返回 (changed_urls, unchanged_urls, source_hashes)
    """
    db = await get_db_cache()
    changed_urls = []
    unchanged_urls = []
    source_hashes = {}
    
    async with aiohttp.ClientSession() as session:
        for url in sources:
            try:
                content, etag, last_modified = await fetch_url_with_etag(session, url)
                current_hash = compute_content_hash(content)
                
                # 从数据库获取缓存的哈希
                cached_hash = await db.get_source_hash(url)
                
                if cached_hash != current_hash:
                    print(f"🔄 源已变更: {url}")
                    changed_urls.append(url)
                    # 更新缓存
                    await db.set_raw_source(url, content, etag, last_modified)
                    await db.set_source_hash(url, current_hash)
                else:
                    print(f"✅ 源无变化: {url}")
                    unchanged_urls.append(url)
                
                source_hashes[url] = current_hash
            except Exception as e:
                print(f"⚠️ 检测源失败 {url}: {e}")
                changed_urls.append(url)  # 检测失败视为有变化
    
    return changed_urls, unchanged_urls, source_hashes

async def fetch_all_sources(sources: list, force_refresh: bool = False) -> dict:
    """
    并行拉取所有源，支持增量更新。
    force_refresh: 强制重新拉取所有源
    """
    db = await get_db_cache()
    results = {}
    
    if not force_refresh:
        # 检测源变化
        changed_urls, unchanged_urls, _ = await check_sources_changed(sources)
        
        # 从缓存加载未变化的源
        for url in unchanged_urls:
            cached = await db.get_raw_source(url)
            if cached:
                results[url] = cached
                print(f"📦 使用缓存: {url}")
            else:
                changed_urls.append(url)  # 缓存丢失，需要重新拉取
        
        need_fetch = changed_urls
    else:
        need_fetch = sources
    
    # 拉取需要更新的源
    if need_fetch:
        print(f"📥 拉取 {len(need_fetch)} 个源...")
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_url_with_etag(session, url) for url in need_fetch]
            fetch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, res in zip(need_fetch, fetch_results):
                if isinstance(res, Exception):
                    print(f"⚠️ 拉取失败 {url}: {res}")
                    # 尝试从缓存获取旧数据
                    cached = await db.get_raw_source(url)
                    if cached:
                        results[url] = cached
                        print(f"📦 拉取失败，使用旧缓存: {url}")
                    else:
                        results[url] = None
                else:
                    content, etag, last_modified = res
                    results[url] = content
                    await db.set_raw_source(url, content, etag, last_modified)
                    # 更新哈希
                    current_hash = compute_content_hash(content)
                    await db.set_source_hash(url, current_hash)
                    print(f"✅ 拉取成功: {url}")
    
    return results
