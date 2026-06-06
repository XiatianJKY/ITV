import asyncio
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from src.config import FFMPEG_ENABLE, TIMEOUT, MAX_WORKERS, FFMPEG_STRICT

_ffprobe_available = None
_thread_pool = None

def get_thread_pool():
    global _thread_pool
    if _thread_pool is None:
        # ffmpeg验证使用更少的并发，避免CPU过载
        _thread_pool = ThreadPoolExecutor(max_workers=min(MAX_WORKERS, 2))
    return _thread_pool

def check_ffprobe_sync():
    try:
        result = subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

async def check_ffprobe():
    global _ffprobe_available
    if _ffprobe_available is not None:
        return _ffprobe_available
    loop = asyncio.get_event_loop()
    _ffprobe_available = await loop.run_in_executor(get_thread_pool(), check_ffprobe_sync)
    if _ffprobe_available:
        print("✅ ffprobe 可用（深度验证已启用）")
    else:
        print("⚠️ ffprobe 不可用，将跳过深度验证")
    return _ffprobe_available

def validate_with_ffprobe_sync(url: str, timeout: int):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
           "-analyzeduration", "3000000", "-probesize", "3000000", url]  # 减少分析时间
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        if result.returncode != 0:
            return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        video_codec = next((s.get("codec_name", "").lower() for s in streams if s.get("codec_type") == "video"), "")
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        valid = has_video or has_audio
        if not valid and not FFMPEG_STRICT:
            valid = True
        return {"valid": valid, "has_video": has_video, "video_codec": video_codec, "has_audio": has_audio}
    except subprocess.TimeoutExpired:
        return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}
    except:
        return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}

async def validate_with_ffprobe(channel, semaphore, pbar):
    async with semaphore:
        if not FFMPEG_ENABLE:
            pbar.update(1)
            return channel, True
        if not await check_ffprobe():
            pbar.update(1)
            return channel, True
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(get_thread_pool(), validate_with_ffprobe_sync, channel.url, TIMEOUT)
        if hasattr(channel, 'video_codec'):
            channel.video_codec = result.get("video_codec", "")
        pbar.update(1)
        return channel, result.get("valid", True)

async def validate_batch(channels: list) -> list:
    if not FFMPEG_ENABLE:
        print("⚙️ ffmpeg 深度验证未启用，跳过")
        return channels
    if not await check_ffprobe():
        print("⚠️ ffprobe 不可用，跳过深度验证，全部频道视为有效")
        return channels
    semaphore = asyncio.Semaphore(min(MAX_WORKERS, 2))
    total = len(channels)
    print(f"🔍 开始 ffmpeg 深度验证，共 {total} 个频道...")
    with tqdm(total=total, desc="ffmpeg验证", unit="个") as pbar:
        tasks = [validate_with_ffprobe(ch, semaphore, pbar) for ch in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = []
    for item in results:
        if isinstance(item, Exception):
            continue
        ch, ok = item
        if ok:
            valid.append(ch)
    print(f"✅ 深度验证完成，通过 {len(valid)}/{total} 个频道")
    return valid

async def validate_with_ffmpeg_batch(channels: list) -> list:
    return await validate_batch(channels)
