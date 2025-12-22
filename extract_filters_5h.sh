#!/bin/bash
# Скрипт для извлечения логов фильтров за последние 5 часов

cd ~/tgbotigorkapa || exit 1

today=$(date +%Y%m%d)
filter_log="logs/filters_${today}.log"
bot_log="logs/bot_${today}.log"

# Получаем текущее время и время 5 часов назад в секундах
now_epoch=$(date +%s)
five_hours_ago_epoch=$((now_epoch - 5*3600))

# Функция для проверки, попадает ли строка лога в диапазон
check_time() {
    local log_line="$1"
    # Извлекаем дату и время из строки: "2025-12-17 12:46:48,123"
    if [[ $log_line =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})\ ([0-9]{2}:[0-9]{2}:[0-9]{2}) ]]; then
        log_date="${BASH_REMATCH[1]}"
        log_time="${BASH_REMATCH[2]}"
        # Преобразуем в epoch
        log_epoch=$(date -d "${log_date} ${log_time}" +%s 2>/dev/null)
        if [ $? -eq 0 ] && [ "$log_epoch" -ge "$five_hours_ago_epoch" ]; then
            return 0
        fi
    fi
    return 1
}

# Очищаем временный файл
> /tmp/filters_5hours.log

# Обрабатываем лог фильтров
if [ -f "$filter_log" ]; then
    while IFS= read -r line; do
        if [[ $line =~ \[BLOCKED\] ]] && check_time "$line"; then
            echo "$line" >> /tmp/filters_5hours.log
        fi
    done < "$filter_log"
fi

# Обрабатываем основной лог
if [ -f "$bot_log" ]; then
    while IFS= read -r line; do
        if [[ $line =~ \[BLOCKED\] ]] && check_time "$line"; then
            echo "$line" >> /tmp/filters_5hours.log
        fi
    done < "$bot_log"
fi

# Сортируем по времени
sort /tmp/filters_5hours.log -o /tmp/filters_5hours.log

echo "✅ Логи за последние 5 часов сохранены в /tmp/filters_5hours.log"
echo "📊 Размер файла: $(wc -l < /tmp/filters_5hours.log) строк"
if [ -s /tmp/filters_5hours.log ]; then
    echo "📅 Первая запись: $(head -1 /tmp/filters_5hours.log | cut -d' ' -f1-2)"
    echo "📅 Последняя запись: $(tail -1 /tmp/filters_5hours.log | cut -d' ' -f1-2)"
fi








