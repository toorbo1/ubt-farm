"""UBT Farm Admin Panel - Full control via web interface."""
from flask import Flask, render_template, request, jsonify, session
import os
import json
from pathlib import Path
import subprocess

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'ubt-admin-secret-key-2026'

PROJECT_DIR = Path(__file__).parent.parent
ENV_FILE = PROJECT_DIR / '.env'


@app.route('/admin')
def admin():
    """Admin panel main page."""
    return render_template('admin.html')


@app.route('/api/env', methods=['GET'])
def get_env():
    """Get current .env variables."""
    env_vars = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                # Hide sensitive values
                if 'KEY' in key or 'TOKEN' in key or 'SECRET' in key:
                    env_vars[key.strip()] = value.strip()[:8] + '...' if value.strip() else ''
                else:
                    env_vars[key.strip()] = value.strip()
    return jsonify(env_vars)


@app.route('/api/env', methods=['POST'])
def update_env():
    """Update .env variables."""
    data = request.json
    lines = []
    updated_keys = []

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in data:
                    lines.append(f"{key}={data[key]}")
                    updated_keys.append(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)

    # Add new keys
    for key, value in data.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}")

    ENV_FILE.write_text('\n'.join(lines))
    return jsonify({'success': True, 'message': f'Updated {len(updated_keys)} variables'})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings from config."""
    try:
        sys_path = str(PROJECT_DIR)
        if sys_path not in __import__('sys').path:
            __import__('sys').path.insert(0, sys_path)

        from config.settings import settings
        return jsonify({
            'video_width': settings.video_width,
            'video_height': settings.video_height,
            'video_fps': settings.video_fps,
            'subtitle_font_size': settings.subtitle_font_size,
            'pollinations_model': settings.pollinations_model,
            'use_ai_video': settings.use_ai_video,
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent server logs."""
    log_file = PROJECT_DIR / 'web_app' / 'server.log'
    if log_file.exists():
        lines = log_file.read_text().splitlines()[-100:]
        return jsonify({'logs': lines})
    return jsonify({'logs': []})


@app.route('/api/files', methods=['GET'])
def list_files():
    """List generated media files."""
    output_dir = PROJECT_DIR / 'test_output'
    files = []
    if output_dir.exists():
        for f in output_dir.glob('*'):
            if f.is_file():
                files.append({
                    'name': f.name,
                    'size_kb': f.stat().st_size / 1024,
                    'modified': f.stat().st_mtime
                })
    return jsonify({'files': sorted(files, key=lambda x: x['modified'], reverse=True)})


@app.route('/api/restart', methods=['POST'])
def restart_server():
    """Restart the Flask server."""
    import sys
    python = sys.executable
    os.execl(python, python, *sys.argv)
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
