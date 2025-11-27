#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отправки сигнала в Telegram канал
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import TelegramBot
import config

async def test_signal_send():
    """Тест отправки сигнала в канал"""
    
    print("=" * 60)
    print("ТЕСТ ОТПРАВКИ СИГНАЛА В TELEGRAM КАНАЛ")
    print("=" * 60)
    
    # Проверка конфигурации
    print(f"\n[1] Проверка конфигурации...")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Установлен' if config.TELEGRAM_BOT_TOKEN else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"   TELEGRAM_CHANNEL_ID: {config.TELEGRAM_CHANNEL_ID if config.TELEGRAM_CHANNEL_ID else '❌ НЕ УСТАНОВЛЕН'}")
    
    if not config.TELEGRAM_BOT_TOKEN:
        print("\n❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
        return False
    
    if not config.TELEGRAM_CHANNEL_ID:
        print("\n❌ ОШИБКА: TELEGRAM_CHANNEL_ID не установлен!")
        return False
    
    # Создание тестового сигнала
    print(f"\n[2] Создание тестового сигнала...")
    test_signal = {
        'signal_id': f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'ticker': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'stop_loss': 49500.0,
        'take_profit_1': 50750.0,
        'take_profit_2': 51250.0,
        'take_profit_3': 51750.0,
        'take_profit_4': 52250.0,
        'risk_percent': 1.0,
        'leverage': 10,
        'timeframe': '15m',
        'timeframe_higher': '1h',
        'volume_24h': 10000000.0,
        'spread_percent': 0.1,
        'atr_value': 250.0
    }
    
    print(f"   Тикер: {test_signal['ticker']}")
    print(f"   Направление: {test_signal['direction']}")
    print(f"   Entry: {test_signal['entry_price']}")
    print(f"   Stop: {test_signal['stop_loss']}")
    print(f"   TP1: {test_signal['take_profit_1']}")
    
    # Инициализация бота
    print(f"\n[3] Инициализация Telegram бота...")
    try:
        telegram_bot = TelegramBot()
        print("   ✅ Бот инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Отправка сигнала
    print(f"\n[4] Отправка тестового сигнала в канал...")
    print(f"   Канал ID: {config.TELEGRAM_CHANNEL_ID}")
    
    try:
        result = await telegram_bot.send_signal(test_signal)
        
        if result:
            print(f"\n✅ УСПЕХ! Тестовый сигнал отправлен в канал!")
            print(f"   Проверь канал: {config.TELEGRAM_CHANNEL_ID}")
            return True
        else:
            print(f"\n❌ ОШИБКА: Сигнал не отправлен (send_signal вернул False)")
            return False
            
    except Exception as e:
        print(f"\n❌ ОШИБКА при отправке: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Закрытие бота
        try:
            if hasattr(telegram_bot, 'app'):
                await telegram_bot.app.shutdown()
        except:
            pass

async def main():
    """Главная функция"""
    try:
        result = await test_signal_send()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

