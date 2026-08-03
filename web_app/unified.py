"""UBT Farm - Unified Web App with Chat and Public Access."""
from flask import Flask, render_template, request, jsonify
import asyncio
import sys
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.llm_client import LLMClient
from core.image_gen import get_image_generator
from core.video_ai import get_img2video_generator
from video_engine.builder import VideoBuilder

app = Flask(__name__, template_folder='templates', static_folder=str(Path('test_output')))
app.config['UPLOAD_FOLDER'] = Path('test_output')
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

# Хранилище сообщений чата
chat_messages = []


@app.route('/')
def index():
    """Главная страница - генератор."""
    return render_template('unified.html')


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
        import base64
        img_data = base64.b64encode(out.read_bytes()).decode()
        return {'path': f'data:image/jpeg;base64,{img_data}', 'size_kb': out.stat().st_size / 1024}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do())
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Чат с Claude."""
    data = request.json
    message = data.get('message', '')

    # Сохраняем сообщение пользователя
    chat_messages.append({'role': 'user', 'content': message, 'time': time.strftime('%H:%M:%S')})

    # Отвечаем через LLM
    async def get_response():
        client = LLMClient()
        # Создаём промпт для Claude
        context = "\n".join([f"{m['role']}: {m['content']}" for m in chat_messages[-5:]])
        prompt = f"""Ты — помощник UBT Farm. Отвечай кратко и по делу.

История чата:
{context}

Вопрос пользователя: {message}

Ответ:"""

        try:
            response = await client.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {client.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Ошибка API: {response.status_code}"
        except Exception as e:
            return f"Ошибка: {str(e)}"

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response_text = loop.run_until_complete(get_response())
        loop.close()

        # Сохраняем ответ
        chat_messages.append({'role': 'assistant', 'content': response_text, 'time': time.strftime('%H:%M:%S')})

        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/history')
def get_chat_history():
    """Получить историю чата."""
    return jsonify({'messages': chat_messages[-50:]})  # Последние 50 сообщений


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    app.run(debug=True, host='0.0.0.0', port=args.port)
