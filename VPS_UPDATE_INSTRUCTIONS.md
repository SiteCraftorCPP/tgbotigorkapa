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

**ВАЖНО: Добавление полей для системы ресетов**
```bash
cd ~/tgbotigorkapa
python3 add_reset_fields.py
```

Эта миграция добавляет поля `reset_level` и `reset_price` в таблицу `signals` для автоматических ресетов при падении цены.

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
cd ~/tgbotigorkapa && sudo systemctl stop tgbotigorkapa && git pull origin master && python3 add_reset_fields.py && sudo systemctl start tgbotigorkapa && sudo systemctl status tgbotigorkapa
```

