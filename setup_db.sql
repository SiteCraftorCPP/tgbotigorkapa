-- Скрипт для создания базы данных
-- Запустите: psql -U postgres -f setup_db.sql

-- Создание базы данных
CREATE DATABASE crypto_signals;

-- Подключение к новой БД
\c crypto_signals

-- База готова, таблицы создаст бот автоматически при первом запуске

