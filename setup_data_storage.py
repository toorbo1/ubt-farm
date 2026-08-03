#!/usr/bin/env python3
"""
Настройка постоянного хранилища /data для Amvera Cloud
Копирует важные файлы и базы данных в /data
"""
import os
import shutil
from pathlib import Path

DATA_DIR = Path("/data")
PROJECT_DIR = Path(__file__).resolve().parent

# Файлы и директории, которые нужно сохранить
PERSISTENT_FILES = [
    "logs.db",           # База данных логов
    ".env",              # Конфигурация
    "profiles/",         # Профили пользователей
    "output/",           # Выведенные видео
]

def setup_persistent_storage():
    """Настроить постоянное хранилище"""
    print(f"Настраиваю постоянное хранилище в {DATA_DIR}...")

    # Создаем директорию /data если её нет
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for item in PERSISTENT_FILES:
        src = PROJECT_DIR / item
        dst = DATA_DIR / item

        if src.exists():
            if src.is_file():
                shutil.copy2(src, dst)
                print(f"  Скопирован файл: {item}")
            elif src.is_dir():
                if dst.exists():
                    # Копируем только новые файлы
                    for file_path in src.rglob("*"):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(src)
                            dst_path = dst / rel_path
                            dst_path.parent.mkdir(parents=True, exist_ok=True)
                            if not dst_path.exists():
                                shutil.copy2(file_path, dst_path)
                else:
                    shutil.copytree(src, dst)
                print(f"  Скопирована директория: {item}")
        else:
            # Если файла нет, создаем пустую директорию
            dst.mkdir(parents=True, exist_ok=True)
            print(f"  Создана пустая директория: {item}")

    # Создаем символические ссылки
    for item in PERSISTENT_FILES:
        src = PROJECT_DIR / item
        dst = DATA_DIR / item

        if not src.exists() and dst.exists():
            # Создаем symlink если исходного файла нет
            try:
                if dst.is_file():
                    src.symlink_to(dst)
                elif dst.is_dir():
                    src.symlink_to(dst, target_is_directory=True)
                print(f"  Создан symlink: {item} -> /data/{item}")
            except OSError as e:
                print(f"  Не удалось создать symlink для {item}: {e}")

    print("Постоянное хранилище настроено!")

if __name__ == "__main__":
    setup_persistent_storage()
