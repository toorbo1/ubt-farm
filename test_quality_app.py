"""Тест качества генерации видео/картинок — GUI приложение."""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from core.llm_client import LLMClient
from core.image_gen import get_image_generator
from core.video_ai import get_img2video_generator
from video_engine.builder import VideoBuilder


class QualityTester:
    def __init__(self, root):
        self.root = root
        root.title("UBT Quality Tester - Детальные сценарии")
        root.geometry("900x700")

        # Тема
        ttk.Style().configure("TButton", padding=5)

        # Ввод топика
        frame = ttk.Frame(root, padding=10)
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Топик:").pack(side=tk.LEFT)
        self.topic_var = tk.StringVar(value="искусственный интеллект и нейросети")
        self.topic_entry = ttk.Entry(frame, textvariable=self.topic_var, width=40)
        self.topic_entry.pack(side=tk.LEFT, padx=5)

        # Кнопки
        btn_frame = ttk.Frame(root, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="📝 Сценарий", command=self.test_script).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🖼 Картинка", command=self.test_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🎬 Видео", command=self.test_video).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="▶ Полный цикл", command=self.test_full).pack(side=tk.LEFT, padx=2)

        # Панель с вкладками
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Лог
        log_frame = ttk.Frame(notebook)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        notebook.add(log_frame, text="Лог")

        # Сценарий
        script_frame = ttk.Frame(notebook)
        self.script_text = scrolledtext.ScrolledText(script_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.script_text.pack(fill=tk.BOTH, expand=True)
        notebook.add(script_frame, text="Сценарий")

        # Галерея
        gallery_frame = ttk.Frame(notebook)
        self.gallery_canvas = tk.Canvas(gallery_frame, bg='#2b2b2b')
        scrollbar_y = ttk.Scrollbar(gallery_frame, orient=tk.VERTICAL, command=self.gallery_canvas.yview)
        self.gallery_inner = ttk.Frame(self.gallery_canvas)
        self.gallery_inner.bind(
            "<Configure>",
            lambda e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
        )
        self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor='nw')
        self.gallery_canvas.configure(yscrollcommand=scrollbar_y.set)
        self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        notebook.add(gallery_frame, text="Галерея")

        # Прогресс-бар
        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Статус
        self.status_var = tk.StringVar(value="Готов к тестированию")
        ttk.Label(root, textvariable=self.status_var, font=('Arial', 9)).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Хранилище путей
        self.generated_images = []
        self.generated_videos = []

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update()

    def clear_gallery(self):
        for widget in self.gallery_inner.winfo_children():
            widget.destroy()
        self.generated_images.clear()
        self.generated_videos.clear()

    def add_image_to_gallery(self, img_path, label):
        from PIL import Image, ImageTk
        try:
            im = Image.open(img_path)
            thumb = im.copy()
            thumb.thumbnail((180, 320))  # 9:16 thumbnail
            photo = ImageTk.PhotoImage(thumb)

            frame = ttk.Frame(self.gallery_inner)
            lbl = ttk.Label(frame, image=photo)
            lbl.image = photo  # keep reference
            lbl.pack()
            ttk.Label(frame, text=label, font=('Arial', 8), wraplength=180).pack(pady=2)

            # Кнопка для открытия в полном размере
            btn_frame = ttk.Frame(frame)
            ttk.Button(btn_frame, text="Открыть", command=lambda p=img_path: webbrowser.open(str(p))).pack(side=tk.LEFT, padx=2)
            btn_frame.pack()

            frame.pack(side=tk.LEFT, padx=5, pady=5)
            self.generated_images.append(img_path)
        except Exception as e:
            self.log(f"Gallery error: {e}")

    def show_image_inline(self, img_path):
        """Показать картинку прямо в окне логов."""
        from PIL import Image, ImageTk
        try:
            im = Image.open(img_path)
            # Создать уменьшенную версию для предпросмотра
            preview = im.copy()
            preview.thumbnail((400, 711))  # Половина от 1080x1920

            # Открыть в системном просмотрщике
            import subprocess
            subprocess.Popen(['start', str(img_path)], shell=True)
        except Exception as e:
            self.log(f"Preview error: {e}")

    async def _run_test(self, test_fn):
        self.set_status("Выполнение...")
        self.progress.start()
        try:
            await test_fn()
            self.set_status("Готово ✓")
        except Exception as e:
            self.log(f"❌ ОШИБКА: {e}")
            messagebox.showerror("Ошибка", str(e))
            self.set_status("Ошибка ✗")
        finally:
            self.progress.stop()

    def run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        loop.close()
        return result

    def test_script(self):
        async def do():
            client = LLMClient()
            topic = self.topic_var.get()
            self.log(f"\n{'='*60}")
            self.log(f"📝 Генерация детального сценария: {topic}")
            self.log(f"{'='*60}")

            script_data = await client.generate_scenes(topic)
            scenes = script_data.get("scenes", [])
            highlights = script_data.get("highlight_words", [])

            self.log(f"\n✅ Сцен: {len(scenes)}")
            self.log(f"✅ Ключевые слова: {', '.join(highlights[:5])}")

            # Показать в текстовом поле
            self.script_text.delete('1.0', tk.END)
            full_text = ""
            for i, s in enumerate(scenes):
                narration = s.get('narration', '')
                image_prompt = s.get('image_prompt', '')
                duration = s.get('duration', 3)
                full_text += f"Сцена {i+1} ({duration}с):\n{narration}\n\nПромпт: {image_prompt}\n\n"

            self.script_text.insert('1.0', full_text.strip())
            self.log(f"\n{'='*60}\n")
        self.run_async(do())

    def test_image(self):
        async def do():
            gen = get_image_generator()
            out = Path("test_output/test_img.jpg")
            out.parent.mkdir(parents=True, exist_ok=True)

            topic = self.topic_var.get()
            prompt = f"Detailed 2D pixel art, 16-bit retro game aesthetic. A small black pixel cat with glowing green eyes, typing on mechanical keyboard in cyberpunk room with neon lights, floating data particles, vertical 9:16 portrait, rich dithering and intricate textures"

            self.log(f"\n{'='*60}")
            self.log(f"🖼 Генерация картинки...")
            self.log(f"{'='*60}")

            await gen.generate(prompt, out, seed=42)

            size_kb = out.stat().st_size / 1024
            self.log(f"✅ Размер: {size_kb:.1f} KB ({out.stat().st_size} bytes)")
            self.log(f"✅ Разрешение: 1080x1920")

            # Открыть картинку в окне
            self.show_image_inline(out)

            # Добавить в галерею
            self.clear_gallery()
            self.add_image_to_gallery(out, "Test Image")
            self.log(f"{'='*60}\n")
        self.run_async(do())

    def test_video(self):
        async def do():
            img_gen = get_image_generator()
            vid_gen = get_img2video_generator()
            img_path = Path("test_output/test_vid_img.jpg")
            vid_path = Path("test_output/test_vid.mp4")
            img_path.parent.mkdir(parents=True, exist_ok=True)

            topic = self.topic_var.get()
            prompt = "Detailed 2D pixel art, 16-bit retro game aesthetic. A small black pixel cat with glowing green eyes, typing on mechanical keyboard in cyberpunk room with neon lights"

            self.log(f"\n{'='*60}")
            self.log(f"🎬 Генерация видео (3 секунды)")
            self.log(f"{'='*60}")

            self.log(f"1️⃣ Генерация картинки...")
            await img_gen.generate(prompt, img_path, seed=123)
            size_kb = img_path.stat().st_size / 1024
            self.log(f"   ✅ Картинка: {size_kb:.1f} KB")

            self.log(f"2️⃣ Генерация видео...")
            await vid_gen.generate(img_path, prompt, vid_path, duration=3)
            size_mb = vid_path.stat().st_size / (1024*1024)
            self.log(f"   ✅ Видео: {size_mb:.2f} MB")
            self.log(f"   ✅ Путь: {vid_path.absolute()}")
            self.log(f"{'='*60}\n")

            # Добавить в галерею
            self.clear_gallery()
            self.add_image_to_gallery(img_path, "Video Source")
            self.generated_videos.append(vid_path)
        self.run_async(do())

    def test_full(self):
        async def do():
            builder = VideoBuilder()
            builder.output_dir = Path("test_output")
            builder.scenes_dir = builder.output_dir / "scenes"
            builder.scenes_dir.mkdir(parents=True, exist_ok=True)

            topic = self.topic_var.get()
            self.log(f"\n{'='*60}")
            self.log(f"▶ ПОЛНЫЙ ЦИКЛ: {topic}")
            self.log(f"{'='*60}")

            self.log("\n1️⃣ Сценарий...")
            from core.llm_client import LLMClient
            llm = LLMClient()
            script_data = await llm.generate_scenes(topic)
            scenes = script_data.get("scenes", [])
            highlights = script_data.get("highlight_words", [])

            # Показать полный сценарий
            self.script_text.delete('1.0', tk.END)
            full_text = f"ТЕМА: {topic}\n\n"
            for i, s in enumerate(scenes):
                narration = s.get('narration', '')
                image_prompt = s.get('image_prompt', '')
                duration = s.get('duration', 3)
                full_text += f"═══ СЦЕНА {i+1} ({duration}с) ═══\n{narration}\n\n🎨 {image_prompt}\n\n"
            self.script_text.insert('1.0', full_text)

            self.log(f"   ✅ {len(scenes)} сцен")

            self.log("\n2️⃣ Озвучка...")
            built = await builder.synthesize_scenes(scenes)
            total_audio = sum(s.duration for s in built)
            self.log(f"   ✅ {len(built)} аудиофайлов, ~{total_audio:.1f}с")

            self.log("\n3️⃣ Картинки...")
            await builder.generate_images(built)
            self.log(f"   ✅ {len(built)} картинок сгенерировано")

            # Очистить галерею и добавить картинки
            self.clear_gallery()
            for scene in built:
                if scene.image_path:
                    self.add_image_to_gallery(scene.image_path, f"Сцена {scene.index+1}")

            self.log("\n4️⃣ Видео из картинок...")
            await builder.generate_clips(built)
            self.log(f"   ✅ {len(built)} видеоклипов создано")

            self.log("\n5️⃣ Финальная сборка...")
            output = await builder.assemble(built, highlights)
            size_mb = output.stat().st_size / (1024*1024)
            self.log(f"   ✅ ГОТОВО: {output.name}")
            self.log(f"   ✅ Размер: {size_mb:.2f} MB")
            self.log(f"   ✅ Длительность: ~{total_audio:.1f}с")
            self.log(f"   ✅ Путь: {output.absolute()}")
            self.log(f"\n{'='*60}\n")

            self.generated_videos.append(output)
            messagebox.showinfo("Успех", f"Видео создано!\n\nФайл: {output.name}\nРазмер: {size_mb:.2f} MB")
        self.run_async(do())


if __name__ == "__main__":
    root = tk.Tk()
    app = QualityTester(root)
    root.mainloop()
