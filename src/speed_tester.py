import asyncio
import aiohttp
import time
from tqdm import tqdm
from src.config import HEADERS, TIMEOUT, MAX_WORKERS, ENABLE_IP_RESOLVE
from src.ip_resolver import get_resolver

async def probe_channel(session, channel, semaphore, pbar):
    async with semaphore:
        url = channel.url
        try:
            start = time.time()
            async with session.head(url, timeout=TIMEOUT, allow_redirects=True, headers=HEADERS) as resp:
                latency = int((time.time() - start) * 1000)
                if resp.status == 200:
                    ip_info = None
                    if ENABLE_IP_RESOLVE:
                        resolver = get_resolver()
                        if resolver.is_available:
                            ip_info = resolver.resolve_channel_ip(channel)
                    pbar.update(1)
                    return channel, latency, True, ip_info
                else:
                    pbar.update(1)
                    return channel, latency, False, None
        except Exception:
            pbar.update(1)
            return channel, 0, False, None

async def test_channels_concurrent(channels_dict: dict) -> list:
    channels = list(channels_dict.values())
    total = len(channels)
    print(f"⚡ 开始测速，共 {total} 个频道，并发数 {MAX_WORKERS}...")
    
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    connector = aiohttp.TCPConnector(limit=MAX_WORKERS, limit_per_host=5, ttl_dns_cache=300)
    timeout_config = aiohttp.ClientTimeout(total=TIMEOUT + 5, connect=TIMEOUT, sock_read=TIMEOUT)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout_config) as session:
        with tqdm(total=total, desc="测速进度", unit="个") as pbar:
            tasks = [probe_channel(session, ch, semaphore, pbar) for ch in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid = []
    for res in results:
        if isinstance(res, Exception):
            continue
        ch, latency, ok, ip_info = res
        if ok:
            ch.latency = latency
            ch.ip_info = ip_info
            valid.append(ch)
    
    valid.sort(key=lambda x: getattr(x, 'latency', 9999))
    print(f"✅ 测速完成，有效频道 {len(valid)}/{total}")
    return valid
