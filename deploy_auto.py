"""
Автоматический деплой UBT Farm на сервер 144.31.25.159
Использует paramiko с различными методами аутентификации
"""
import os
import sys
import time
import traceback
from pathlib import Path

# Настройки сервера
HOST = "144.31.25.159"
USER = "root"
PASSWORD = "BYAgu5iR5RgE0XuA"
PORT = 22
REMOTE_DIR = "/opt/ubt-farm"

PROJECT_DIR = Path(__file__).resolve().parent

EXCLUDE_DIRS = {".git", "__pycache__", "venv", "node_modules", ".idea", ".vscode"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".mp4"}
EXCLUDE_FILES = {".env"}


def should_exclude(path: Path, rel: str) -> bool:
    """Проверяет, нужно ли исключить файл из деплоя"""
    parts = rel.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    if path.suffix in EXCLUDE_EXTS:
        return True
    if path.name in EXCLUDE_FILES:
        return True
    return False


def safe_print(msg: str) -> None:
    """Безопасный вывод для Windows"""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode(), flush=True)


def connect_with_retry(max_attempts=5):
    """Попытка подключения с повторами"""
    import paramiko

    for attempt in range(1, max_attempts + 1):
        safe_print(f"  Попытка {attempt}/{max_attempts}...")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Пробуем разные методы подключения
            try:
                client.connect(
                    HOST, PORT, USER, PASSWORD,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30
                )
                safe_print(f"  [OK] Подключено (попытка {attempt})")
                return client
            except Exception as e:
                safe_print(f"  Ошибка: {e}")

        except Exception as e:
            safe_print(f"  Ошибка попытки {attempt}: {e}")
            if attempt < max_attempts:
                time.sleep(3)

    return None


def deploy():
    """Основная функция деплоя"""
    import paramiko

    safe_print("=" * 60)
    safe_print("  UBT Farm - автоматический деплой")
    safe_print(f"  Сервер: {HOST}:{PORT}")
    safe_print(f"  Проект: {PROJECT_DIR}")
    safe_print("=" * 60)

    # 1. Подключение
    safe_print("\n[1/7] Подключение к серверу...")
    client = connect_with_retry()

    if not client:
        safe_print("\n  [FAIL] Не удалось подключиться к серверу")
        safe_print("\n  Возможные причины:")
        safe_print("  - Пароль неверный или истек")
        safe_print("  - SSH настроен только на key-based аутентификацию")
        safe_print("  - Fail2ban заблокировал IP")
        safe_print("  - SSH сервер не запущен")
        safe_print("\n  Решение:")
        safe_print("  1. Проверьте пароль через панель хостинга")
        safe_print("  2. Используйте веб-консоль хостинга для проверки доступа")
        safe_print("  3. Свяжитесь с поддержкой хостинга")
        return False

    sftp = client.open_sftp()

    try:
        # 2. Создание директорий
        safe_print("\n[2/7] Создание директорий...")
        dirs = [
            REMOTE_DIR,
            f"{REMOTE_DIR}/bot",
            f"{REMOTE_DIR}/config",
            f"{REMOTE_DIR}/core",
            f"{REMOTE_DIR}/video_engine",
            f"{REMOTE_DIR}/uploader",
            f"{REMOTE_DIR}/uniqueizer",
            f"{REMOTE_DIR}/storage",
            f"{REMOTE_DIR}/assets",
            f"{REMOTE_DIR}/assets/backgrounds",
            f"{REMOTE_DIR}/assets/fonts",
            f"{REMOTE_DIR}/output",
            f"{REMOTE_DIR}/logs",
            f"{REMOTE_DIR}/profiles",
        ]

        for d in dirs:
            try:
                sftp.stat(d)
            except FileNotFoundError:
                sftp.mkdir(d)
                safe_print(f"  > Создана {d}")
        safe_print("  [OK] Директории готовы")

        # 3. Загрузка файлов
        safe_print("\n[3/7] Загрузка файлов...")
        uploaded = 0
        skipped = 0

        for file_path in PROJECT_DIR.rglob("*"):
            if not file_path.is_file():
                continue

            rel = str(file_path.relative_to(PROJECT_DIR))

            if should_exclude(file_path, rel):
                skipped += 1
                continue

            remote_path = f"{REMOTE_DIR}/{rel.replace(os.sep, '/')}"

            try:
                sftp.put(str(file_path), remote_path)
                uploaded += 1
                if uploaded % 50 == 0:
                    safe_print(f"  > Загружено {uploaded} файлов...")
            except Exception as e:
                safe_print(f"  > ! Ошибка {rel}: {e}")

        safe_print(f"  [OK] Загружено {uploaded} файлов (пропущено {skipped})")

        # 4. Установка зависимостей
        safe_print("\n[4/7] Установка зависимостей...")
        commands = [
            ("apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl > /dev/null 2>&1", "Пакеты"),
            ("command -v node || (curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1 && apt-get install -y -qq nodejs > /dev/null 2>&1)", "Node.js"),
            ("npm install -g pm2 > /dev/null 2>&1 || true", "PM2"),
            (f"cd {REMOTE_DIR} && python3 -m venv venv", "Python venv"),
            (f"cd {REMOTE_DIR} && venv/bin/pip install -q -U pip setuptools wheel", "Pip update"),
        ]

        for cmd, label in commands:
            try:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code == 0:
                    safe_print(f"  [OK] {label}")
                else:
                    err = stderr.read().decode().strip()[:100]
                    safe_print(f"  [WARN] {label} ({err})")
            except Exception as e:
                safe_print(f"  [WARN] {label}: {str(e)[:100]}")

        # Установка requirements.txt
        safe_print("  Установка Python зависимостей...")
        try:
            stdin, stdout, stderr = client.exec_command(
                f"cd {REMOTE_DIR} && venv/bin/pip install -q -r requirements.txt",
                timeout=300
            )
            exit_code = stdout.channel.recv_exit_status()
            if exit_code == 0:
                safe_print("  [OK] requirements.txt установлен")
            else:
                err = stderr.read().decode().strip()[:100]
                safe_print(f"  [WARN] {err}")
        except Exception as e:
            safe_print(f"  [WARN] {str(e)[:100]}")

        # Playwright
        safe_print("  Установка Playwright...")
        try:
            stdin, stdout, stderr = client.exec_command(
                f"cd {REMOTE_DIR} && venv/bin/python3 -m playwright install chromium --with-deps > /dev/null 2>&1",
                timeout=600
            )
            stdout.channel.recv_exit_status()
            safe_print("  [OK] Playwright установлен")
        except Exception as e:
            safe_print(f"  [WARN] Playwright: {str(e)[:100]}")

        # 5. PM2 конфигурация
        safe_print("\n[5/7] Настройка PM2...")
        pm2_config = f"""const path = require('path');
module.exports = {{
  apps: [
    {{
      name: "ubt-bot1",
      script: "{REMOTE_DIR}/bot/run_bot.py",
      interpreter: "{REMOTE_DIR}/venv/bin/python3",
      args: "--bot 1",
      cwd: "{REMOTE_DIR}",
      error_file: "{REMOTE_DIR}/logs/bot1-error.log",
      out_file: "{REMOTE_DIR}/logs/bot1-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    }},
    {{
      name: "ubt-bot2",
      script: "{REMOTE_DIR}/bot/run_bot.py",
      interpreter: "{REMOTE_DIR}/venv/bin/python3",
      args: "--bot 2",
      cwd: "{REMOTE_DIR}",
      error_file: "{REMOTE_DIR}/logs/bot2-error.log",
      out_file: "{REMOTE_DIR}/logs/bot2-out.log",
      merge_logs: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      restart_delay: 5000,
    }},
  ],
}};
"""
        with sftp.open(f"{REMOTE_DIR}/ecosystem.config.js", "w") as f:
            f.write(pm2_config)
        safe_print("  [OK] PM2 ecosystem загружен")

        # 6. Запуск ботов
        safe_print("\n[6/7] Запуск ботов...")
        pm2_cmds = [
            f"cd {REMOTE_DIR} && pm2 delete ubt-bot1 ubt-bot2 2>/dev/null; pm2 start ecosystem.config.js",
            f"cd {REMOTE_DIR} && pm2 save",
            "pm2 startup systemd -u root --hp /root 2>/dev/null || true",
        ]

        for cmd in pm2_cmds:
            try:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
                stdout.channel.recv_exit_status()
                safe_print(f"  [OK] Выполнено: {cmd[:60]}")
            except Exception as e:
                safe_print(f"  [WARN] {str(e)[:80]}")

        # Проверка статуса
        safe_print("\n  Статус ботов:")
        stdin, stdout, stderr = client.exec_command("pm2 status")
        output = stdout.read().decode(errors="replace")
        for line in output.split("\n")[:10]:
            if line.strip():
                safe_print(f"  {line}")

        # 7. Logrotate
        safe_print("\n[7/7] Настройка logrotate...")
        logrotate_conf = f"""{REMOTE_DIR}/logs/*.log {{
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}}
"""
        try:
            with sftp.open("/etc/logrotate.d/ubt-farm", "w") as f:
                f.write(logrotate_conf)
            safe_print("  [OK] Logrotate настроен")
        except Exception as e:
            safe_print(f"  [WARN] Logrotate: {e}")

        # Итог
        safe_print("\n" + "=" * 60)
        safe_print("  ДЕПЛОЙ ЗАВЕРШЕН!")
        safe_print("=" * 60)
        safe_print(f"\n  Полезные команды:")
        safe_print(f"  Логи бота 1: pm2 logs ubt-bot1 --lines 20")
        safe_print(f"  Логи бота 2: pm2 logs ubt-bot2 --lines 20")
        safe_print(f"  Редактировать .env: nano {REMOTE_DIR}/.env")
        safe_print(f"  Перезапуск: cd {REMOTE_DIR} && pm2 restart all")

        return True

    except Exception as e:
        safe_print(f"\n  [FAIL] Ошибка: {e}")
        traceback.print_exc()
        return False

    finally:
        sftp.close()
        client.close()
        safe_print("  SSH соединение закрыто.")


if __name__ == "__main__":
    try:
        success = deploy()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        safe_print("\n\n  [CANCEL] Деплой отменен пользователем")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n  [FATAL] Критическая ошибка: {e}")
        traceback.print_exc()
        sys.exit(1)
