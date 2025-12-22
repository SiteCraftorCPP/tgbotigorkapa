# Инструкция по обновлению бота на VPS

## 1. Остановка бота

```bash
cd ~/tgbotigorkapa
sudo systemctl stop tgbotigorkapa
```

Или принудительно через процессы:
```bash
pkill -f "python.*main.py"
```

## 2. Обновление кода из Git

```bash
cd ~/tgbotigorkapa
git pull origin master
```

## 3. Обновление БД

```bash
cd ~/tgbotigorkapa
python3 update_impulse_db.py
```

Или вручную через SQLite:
```bash
sqlite3 crypto_signals.db "UPDATE bot_config SET value = json_replace(json_replace(value, '$.impulse_body_ratio', 43), '$.impulse_avg_multiplier', 1.05) WHERE key = 'filter_settings';"
```

## 4. Запуск бота

```bash
sudo systemctl start tgbotigorkapa
```

## 5. Проверка статуса

```bash
sudo systemctl status tgbotigorkapa
```

## 6. Просмотр логов

```bash
journalctl -u tgbotigorkapa -f
```

---

## Все команды одной строкой:

```bash
cd ~/tgbotigorkapa && sudo systemctl stop tgbotigorkapa && git pull origin master && python3 update_impulse_db.py && sudo systemctl start tgbotigorkapa && sudo systemctl status tgbotigorkapa
```

