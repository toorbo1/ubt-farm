#!/bin/bash
# Скачивает фоновые видео для UBT Farm
# Запускать на сервере: bash download_backgrounds.sh

set -e
BG_DIR="/opt/ubt-farm/assets/backgrounds"
mkdir -p "$BG_DIR"
cd "$BG_DIR"

echo "Скачиваю фоновые видео..."

# Несколько бесплатных видео с Pexels (через прямые ссылки)
# Паркур, геймплей, природа, ASMR-подобные

# 1. Город/трафик (залипательное)
wget -q -O bg_city_01.mp4 "https://www.pexels.com/download/video/3044151/?h=854&w=480&tpl=pe-edit" 2>/dev/null || true

# 2. Природа/вода
wget -q -O bg_nature_01.mp4 "https://www.pexels.com/download/video/1858011/?h=854&w=480&tpl=pe-edit" 2>/dev/null || true

# 3. Абстракция/неон
wget -q -O bg_neon_01.mp4 "https://www.pexels.com/download/video/2832845/?h=854&w=480&tpl=pe-edit" 2>/dev/null || true

# Если wget не сработал или видео не скачались - генерируем через ffmpeg
if [[ -z "$(ls -A $BG_DIR/*.mp4 2>/dev/null)" ]]; then
    echo "wget не сработал, генерирую фоны через ffmpeg..."

    # Генерируем несколько простых фоновых видео
    for i in 1 2 3; do
        # Цветной градиент с движением
        hue=$(shuf -i 0-360 -n 1)
        ffmpeg -y -f lavfi -i \
            "color=c=#000000:s=1080x1920:d=30:r=30,drawbox=x=100:y=100:w=100:h=100:color=red@0.5:t=max,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255'" \
            -c:v libx264 -preset ultrafast -crf 28 \
            "$BG_DIR/bg_generated_$i.mp4" 2>/dev/null || true
    done

    # Ещё один - круги/волны
    ffmpeg -y -f lavfi -i "cellauto=s=1080x1920:r=30:size=1080x1920" \
        -t 30 -c:v libx264 -preset ultrafast -crf 28 \
        "$BG_DIR/bg_cells.mp4" 2>/dev/null || true
fi

# Проверка
count=$(ls -1 $BG_DIR/*.mp4 2>/dev/null | wc -l)
if [[ "$count" -gt 0 ]]; then
    echo "Готово! Скачано/сгенерировано $count фоновых видео."
    ls -lh $BG_DIR/*.mp4
else
    echo "Ошибка: не удалось получить фоновые видео."
    echo "Скачай вручную и положи в $BG_DIR"
fi
