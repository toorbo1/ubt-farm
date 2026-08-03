"""UBT Traffic Farm - Web Application with full functionality."""
from flask import Flask, render_template, request, jsonify, send_file
import asyncio
import sys
import os
from pathlib import Path
import threading
import time

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.llm_client import LLMClient
from core.image_gen import get_image_generator
from core.video_ai import get_img2video_generator
from video_engine.builder import VideoBuilder
from web_app.storage import storage  # Cloud storage with auto-cleanup

# Use absolute path for static folder to ensure Flask finds files
static_path = Path(__file__).parent.parent / 'test_output'
static_path.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, template_folder='templates', static_folder=str(static_path))
app.config['UPLOAD_FOLDER'] = static_path

# Хранилище задач
tasks = {}

# Авто-очистка каждые 24 часа
def auto_cleanup_loop():
    """Background thread that cleans up old files every hour."""
    while True:
        time.sleep(3600)  # Check every hour
        try:
            deleted = storage.cleanup_old_files(hours=24)
            if deleted > 0:
                print(f"[Auto-Cleanup] Deleted {deleted} old files")
        except Exception as e:
            print(f"[Auto-Cleanup] Error: {e}")

cleanup_thread = threading.Thread(target=auto_cleanup_loop, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html')


@app.route('/static/<filename>')
def serve_static(filename):
    """Serve files from test_output directory."""
    from flask import send_from_directory
    return send_from_directory(str(app.config['UPLOAD_FOLDER']), filename)


@app.route('/api/script', methods=['POST'])
def generate_script():
    """Генерация сценария."""
    data = request.json
    topic = data.get('topic', 'космос')

    async def do():
        client = LLMClient()
        script_data = await client.generate_scenes(topic)
        scenes = script_data.get("scenes", [])
        highlights = script_data.get("highlight_words", [])

        result = []
        for i, s in enumerate(scenes):
            result.append({
                'index': i,
                'narration': s.get('narration', ''),
                'image_prompt': s.get('image_prompt', ''),
                'duration': s.get('duration', 3),
            })

        return {
            'scenes': result,
            'highlights': highlights,
            'full_text': '\n\n'.join([
                f"Сцена {i+1} ({s.get('duration', 3)}с):\n{s.get('narration', '')}\n\nПромпт: {s.get('image_prompt', '')}"
                for i, s in enumerate(scenes)
            ])
        }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do())
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/image', methods=['POST'])
def generate_image():
    """Генерация картинки."""
    data = request.json
    prompt = data.get('prompt', 'pixel art cat')
    seed = data.get('seed', 42)

    async def do():
        gen = get_image_generator()
        out = app.config['UPLOAD_FOLDER'] / f"img_{int(time.time())}.jpg"
        await gen.generate(prompt, out, seed=seed)

        # Return base64 image for immediate display
        import base64
        img_data = base64.b64encode(out.read_bytes()).decode()
        return {
            'path': f'data:image/jpeg;base64,{img_data}',
            'size_kb': out.stat().st_size / 1024,
            'filename': out.name
        }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do())
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video', methods=['POST'])
def generate_video():
    """Генерация видео (Ken Burns)."""
    data = request.json
    input_image_path = data.get('image_path', '')
    duration = data.get('duration', 3)

    async def do():
        img_gen = get_image_generator()
        vid_gen = get_img2video_generator()

        img_file = app.config['UPLOAD_FOLDER'] / f"vid_img_{int(time.time())}.jpg"
        vid_file = app.config['UPLOAD_FOLDER'] / f"vid_{int(time.time())}.mp4"

        # Генерируем картинку если не передана
        if not input_image_path:
            prompt = data.get('prompt', 'pixel art')
            await img_gen.generate(prompt, img_file, seed=123)
            final_image_path = img_file
        else:
            final_image_path = Path(input_image_path)

        await vid_gen.generate(
            final_image_path,
            data.get('prompt', 'animation'),
            vid_file,
            duration
        )

        return {
            'video_path': f'/static/{vid_file.name}',
            'size_mb': vid_file.stat().st_size / (1024*1024)
        }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do())
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/full-pipeline', methods=['POST'])
def full_pipeline():
    """Полный цикл создания видео."""
    data = request.json
    topic = data.get('topic', 'космос')

    task_id = f"task_{int(time.time())}"
    tasks[task_id] = {'status': 'running', 'progress': 0, 'result': None}

    def run_pipeline():
        async def do():
            try:
                builder = VideoBuilder()
                builder.output_dir = app.config['UPLOAD_FOLDER']
                builder.scenes_dir = builder.output_dir / "scenes"
                builder.scenes_dir.mkdir(parents=True, exist_ok=True)

                # 1. Сценарий
                tasks[task_id]['progress'] = 10
                from core.llm_client import LLMClient
                llm = LLMClient()
                script_data = await llm.generate_scenes(topic)
                scenes = script_data.get("scenes", [])
                highlights = script_data.get("highlight_words", [])
                tasks[task_id]['progress'] = 30

                # 2. Озвучка
                built = await builder.synthesize_scenes(scenes)
                tasks[task_id]['progress'] = 50

                # 3. Картинки
                await builder.generate_images(built)
                tasks[task_id]['progress'] = 70

                # 4. Видео
                await builder.generate_clips(built)
                tasks[task_id]['progress'] = 85

                # 5. Сборка
                output = await builder.assemble(built, highlights)
                tasks[task_id]['progress'] = 100
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['result'] = {
                    'video_path': f'/static/{output.name}',
                    'size_mb': output.stat().st_size / (1024*1024),
                    'duration': sum(s.duration for s in built)
                }

            except Exception as e:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['error'] = str(e)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(do())
        loop.close()

    thread = threading.Thread(target=run_pipeline)
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})


@app.route('/api/task-status/<task_id>')
def task_status(task_id):
    """Проверка статуса задачи."""
    task = tasks.get(task_id, {'status': 'not_found'})
    return jsonify(task)


@app.route('/api/gallery')
def get_gallery():
    """Получить список картинок и видео из хранилища."""
    import base64

    images = []
    videos = []

    # Local files
    for f in sorted(app.config['UPLOAD_FOLDER'].glob('*.jpg')):
        img_data = base64.b64encode(f.read_bytes()).decode()
        images.append({
            'name': f.name,
            'url': f'data:image/jpeg;base64,{img_data}',
            'size_kb': f.stat().st_size / 1024
        })

    for f in sorted(app.config['UPLOAD_FOLDER'].glob('*.mp4')):
        videos.append({
            'name': f.name,
            'url': f'/static/{f.name}',
            'size_mb': f.stat().st_size / (1024*1024)
        })

    return jsonify({'images': images, 'videos': videos})


@app.route('/api/cleanup', methods=['POST'])
def manual_cleanup():
    """Ручная очистка старых файлов."""
    deleted = storage.cleanup_old_files(hours=24)
    return jsonify({'deleted': deleted})


@app.route('/api/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """Удалить конкретный файл из хранилища."""
    try:
        file_path = app.config['UPLOAD_FOLDER'] / filename
        if file_path.exists():
            file_path.unlink()
            return jsonify({'success': True, 'message': f'Файл {filename} удалён'})
        else:
            return jsonify({'success': False, 'message': f'Файл {filename} не найден'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    app.run(debug=True, host='0.0.0.0', port=args.port)
