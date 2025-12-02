# Команды для обновления бота на VPS

## 1. Остановить бота
```bash
pkill -9 -f "python.*main.py"
```

## 2. Перейти в директорию проекта
```bash
cd ~/tgbotigorkapa
```

## 3. Активировать виртуальное окружение
```bash
source venv/bin/activate
```

## 4. Получить обновления из Git
```bash
git pull origin master
```

## 5. Проверить изменения (опционально)
```bash
git log --oneline -5
```

## 6. Запустить бота
```bash
nohup python main.py > bot.log 2>&1 &
```

## 7. Проверить, что бот запущен
```bash
ps aux | grep "python.*main.py" | grep -v grep
```

## 8. Проверить логи (опционально)
```bash
tail -f ~/tgbotigorkapa/logs/bot_$(date +%Y%m%d).log
```

---

## Все команды одной строкой:
```bash
pkill -9 -f "python.*main.py" && cd ~/tgbotigorkapa && source venv/bin/activate && git pull origin master && nohup python main.py > bot.log 2>&1 &
```

