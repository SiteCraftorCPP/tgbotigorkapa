# Настройка бота на VPS

## Способ 1: Systemd Service (РЕКОМЕНДУЕТСЯ)

### Установка service:

```bash
cd /root/tgbotigorkapa
sudo cp tgbotigorkapa.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tgbotigorkapa
sudo systemctl start tgbotigorkapa
```

### Управление:

```bash
# Статус
sudo systemctl status tgbotigorkapa

# Остановка
sudo systemctl stop tgbotigorkapa

# Запуск
sudo systemctl start tgbotigorkapa

# Перезапуск
sudo systemctl restart tgbotigorkapa

# Логи
sudo journalctl -u tgbotigorkapa -f
# Или
tail -f /root/tgbotigorkapa/logs/bot_service.log
```

### Преимущества:
- ✅ Автозапуск при перезагрузке сервера
- ✅ Автоматический перезапуск при падении
- ✅ Управление через systemctl
- ✅ Логирование в systemd journal

---

## Способ 2: Screen (Альтернатива)

### Запуск:

```bash
cd /root/tgbotigorkapa
chmod +x start_bot_vps.sh
./start_bot_vps.sh
```

### Управление:

```bash
# Подключиться к сессии
screen -r bot

# Отключиться (не останавливая): Ctrl+A, затем D

# Остановить бота
screen -S bot -X quit

# Список сессий
screen -list
```

---

## Проверка работы

```bash
# Проверить процесс
ps aux | grep "python.*main.py" | grep -v grep

# Проверить логи
tail -f /root/tgbotigorkapa/logs/bot_$(date +%Y%m%d).log

# Проверить последние ошибки
grep -i "error\|exception" /root/tgbotigorkapa/logs/bot_$(date +%Y%m%d).log | tail -20
```

---

## Обновление бота

```bash
cd /root/tgbotigorkapa
git pull
source venv/bin/activate
pip install -r requirements.txt

# Если используете systemd:
sudo systemctl restart tgbotigorkapa

# Если используете screen:
screen -S bot -X quit
./start_bot_vps.sh
```

---

## Решение проблем

### Бот не запускается:

1. Проверить логи:
   ```bash
   tail -50 /root/tgbotigorkapa/logs/bot_$(date +%Y%m%d).log
   ```

2. Проверить .env файл:
   ```bash
   cat /root/tgbotigorkapa/.env
   ```

3. Проверить Python версию:
   ```bash
   /root/tgbotigorkapa/venv/bin/python3 --version
   ```

4. Проверить зависимости:
   ```bash
   cd /root/tgbotigorkapa
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Бот падает:

1. Проверить ошибки в логах
2. Проверить доступность API (XT.com, Telegram)
3. Проверить место на диске: `df -h`
4. Проверить память: `free -h`

