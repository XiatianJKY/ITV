# src/web/api.py
"""Web 管理界面 REST API"""

import json
from pathlib import Path
from flask import Blueprint, request, jsonify
from src.config import (
    OUTPUT_DIR, MAX_WORKERS, TIMEOUT, FFMPEG_ENABLE,
    MAX_SOURCES_PER_CHANNEL, DEMO_MATCH_MODE,
    CACHE_RAW_HOURS, CACHE_SPEED_HOURS
)
from src.stable.manager import StableManager
from src.source_pool.discoverer import SourceDiscoverer
from src.candidate.observer import CandidateObserver
from src.web.db import get_quality_history, get_all_channels_with_history, record_quality

api_bp = Blueprint('api', __name__, url_prefix='/api')


def get_channel_category(name: str) -> str:
    """根据频道名判断分类"""
    if name.startswith('CCTV') or '央视' in name:
        return '央视'
    if '卫视' in name:
        return '卫视'
    if any(kw in name for kw in ['港', '澳', '台', '凤凰', '翡翠', '明珠', 'TVB', '东森', '民视', '台视', '华视', '中视', '三立', '纬来']):
        return '港澳台'
    if '频道' in name:
        return '地方'
    return '其他'


@api_bp.route('/status')
def get_status():
    stable_mgr = StableManager()
    stable_sources = stable_mgr.get_active_sources()
    discoverer = SourceDiscoverer()
    pool_stats = discoverer.get_statistics()
    observer = CandidateObserver()
    candidate_stats = observer.get_statistics()
    stats_file = OUTPUT_DIR / "stats.json"
    last_run = None
    if stats_file.exists():
        with open(stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_run = data.get('timestamp')
    return jsonify({
        'stable_count': len(stable_sources),
        'fixed_count': sum(1 for s in stable_sources.values() if s.is_fixed),
        'pool_total': pool_stats.get('total', 0),
        'candidate_observing': candidate_stats.get('observing', 0),
        'last_run': last_run,
        'status': 'running'
    })


@api_bp.route('/channels')
def get_channels():
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '')
    stable_mgr = StableManager()
    sources = stable_mgr.get_active_sources()
    channels = []
    for name, src in sources.items():
        if not src.url:
            continue
        if search and search not in name.lower():
            continue
        cat = get_channel_category(name)
        if category and cat != category:
            continue
        channels.append({
            'name': name,
            'url': src.url,
            'latency': src.latency,
            'codec': src.video_codec,
            'is_fixed': src.is_fixed,
            'category': cat,
            'last_verified': src.last_verified.isoformat() if src.last_verified else None
        })
    channels.sort(key=lambda x: x['name'])
    return jsonify(channels)


@api_bp.route('/fixed_sources', methods=['GET'])
def get_fixed_sources():
    stable_mgr = StableManager()
    fixed = {name: src.url for name, src in stable_mgr.stable_sources.items() if src.is_fixed}
    return jsonify(fixed)


@api_bp.route('/fixed_sources', methods=['POST'])
def add_fixed_source():
    data = request.get_json()
    name = data.get('name')
    url = data.get('url')
    if not name or not url:
        return jsonify({'error': '缺少频道名或URL'}), 400
    stable_mgr = StableManager()
    if stable_mgr.set_fixed_source(name, url):
        return jsonify({'success': True, 'message': f'已添加固定源 {name}'})
    else:
        return jsonify({'error': '添加失败'}), 500


@api_bp.route('/fixed_sources/<name>', methods=['DELETE'])
def delete_fixed_source(name):
    stable_mgr = StableManager()
    if name in stable_mgr.stable_sources and stable_mgr.stable_sources[name].is_fixed:
        # 删除固定源（将其标记为非固定，但不删除条目）
        stable_mgr.stable_sources[name].is_fixed = False
        stable_mgr.stable_sources[name].status = 'active'  # 确保状态正常
        stable_mgr._save()
        return jsonify({'success': True, 'message': f'已移除固定源 {name}'})
    return jsonify({'error': '固定源不存在'}), 404


@api_bp.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        'max_workers': MAX_WORKERS,
        'timeout': TIMEOUT,
        'ffmpeg_enable': FFMPEG_ENABLE,
        'max_sources_per_channel': MAX_SOURCES_PER_CHANNEL,
        'demo_match_mode': DEMO_MATCH_MODE,
        'cache_raw_hours': CACHE_RAW_HOURS,
        'cache_speed_hours': CACHE_SPEED_HOURS,
    })


@api_bp.route('/config', methods=['POST'])
def update_config():
    data = request.get_json()
    # 写入 .env 文件（仅演示，实际可写入配置数据库）
    env_path = Path('.env')
    # 读取现有内容，更新或追加
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    # 转换键名
    key_map = {
        'max_workers': 'MAX_WORKERS',
        'timeout': 'TIMEOUT',
        'ffmpeg_enable': 'FFMPEG_ENABLE',
        'max_sources_per_channel': 'MAX_SOURCES_PER_CHANNEL',
        'demo_match_mode': 'DEMO_MATCH_MODE',
    }
    new_lines = []
    updated_keys = set()
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith('#'):
            key = line_stripped.split('=')[0].strip()
            if key in key_map.values():
                updated_keys.add(key)
                new_value = data.get(key_map[key], None)
                if new_value is not None:
                    new_lines.append(f"{key}={new_value}\n")
                    continue
        new_lines.append(line)
    # 添加未更新的键
    for k, env_key in key_map.items():
        if env_key not in updated_keys and data.get(k) is not None:
            new_lines.append(f"{env_key}={data[k]}\n")
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    return jsonify({'success': True, 'message': '配置已更新，请重启服务生效。'})


@api_bp.route('/quality/<channel_name>')
def get_quality(channel_name):
    days = request.args.get('days', 7, type=int)
    history = get_quality_history(channel_name, days)
    return jsonify(history)


@api_bp.route('/quality/all')
def get_all_quality():
    days = request.args.get('days', 7, type=int)
    data = get_all_channels_with_history(days)
    return jsonify(data)
