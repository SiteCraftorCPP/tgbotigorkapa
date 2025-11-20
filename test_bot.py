"""
Тестовый скрипт для проверки работы бота
"""

import asyncio
from exchange.xt_client import XTClient
from analysis.signal_generator import SignalGenerator
import pandas as pd


async def test_exchange_connection():
    """Тест подключения к бирже"""
    print("🔗 Тестирование подключения к XT.com...")
    
    client = XTClient()
    
    try:
        # Тест получения тикера
        ticker = await client.get_ticker('BTC/USDT')
        if ticker:
            print(f"✅ Текущая цена BTC/USDT: ${ticker['last']}")
        else:
            print("❌ Не удалось получить тикер")
            return False
        
        # Тест получения OHLCV
        df = await client.get_ohlcv('BTC/USDT', '1h', limit=100)
        if not df.empty:
            print(f"✅ Получено {len(df)} свечей (1h)")
            print(f"   Последняя цена закрытия: ${df['close'].iloc[-1]:.2f}")
        else:
            print("❌ Не удалось получить OHLCV")
            return False
        
        # Тест получения списка символов
        symbols = await client.get_all_futures_symbols()
        if symbols:
            print(f"✅ Доступно {len(symbols)} фьючерсных пар")
            print(f"   Примеры: {', '.join(symbols[:5])}")
        else:
            print("❌ Не удалось получить список символов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        client.close()


async def test_signal_generation():
    """Тест генерации сигналов"""
    print("\n📊 Тестирование генерации сигналов...")
    
    client = XTClient()
    
    try:
        # Получение данных для анализа
        df = await client.get_ohlcv('BTC/USDT', '1h', limit=500)
        
        if df.empty:
            print("❌ Нет данных для анализа")
            return False
        
        print(f"✅ Загружено {len(df)} свечей для анализа")
        
        # Генерация сигнала
        generator = SignalGenerator('BTC/USDT', '1h', df)
        signal = generator.generate_signal()
        
        if signal:
            print(f"\n🎯 Сгенерирован сигнал:")
            print(f"   ID: {signal['signal_id']}")
            print(f"   Направление: {signal['direction']}")
            print(f"   Вход: ${signal['entry_price']}")
            print(f"   Стоп: ${signal['stop_loss']}")
            print(f"   TP1: ${signal['take_profit_1']}")
            print(f"   TP2: ${signal['take_profit_2']}")
            print(f"   AI Score: {signal['ai_score']}/100")
            print(f"   Таймфрейм: {signal['timeframe']}")
        else:
            print("⚠️ Сигнал не сгенерирован (не прошёл фильтры)")
            print("   Попробуйте:")
            print("   - Снизить MIN_AI_SCORE в .env")
            print("   - Проверить другие пары")
            print("   - Проверить другие таймфреймы")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


async def test_technical_analysis():
    """Тест технического анализа"""
    print("\n📈 Тестирование технических индикаторов...")
    
    client = XTClient()
    
    try:
        from analysis.indicators import TechnicalAnalysis
        
        df = await client.get_ohlcv('BTC/USDT', '1h', limit=500)
        
        if df.empty:
            print("❌ Нет данных для анализа")
            return False
        
        ta = TechnicalAnalysis(df)
        ta.calculate_all_indicators()
        
        if ta.df.empty:
            print("❌ Ошибка расчёта индикаторов")
            return False
        
        last = ta.df.iloc[-1]
        
        print("✅ Индикаторы рассчитаны:")
        print(f"   EMA 50: ${last['ema_50']:.2f}")
        print(f"   EMA 200: ${last['ema_200']:.2f}")
        print(f"   RSI: {last['rsi']:.2f}")
        print(f"   MACD: {last['macd']:.4f}")
        print(f"   ATR: ${last['atr']:.2f}")
        
        # Получение сигналов
        trend = ta.get_trend_signal()
        momentum = ta.get_momentum_signal()
        volume = ta.get_volume_signal()
        volatility = ta.get_volatility_score()
        
        print(f"\n   Тренд: {trend['direction']} (Score: {trend['score']})")
        print(f"   Моментум: Score {momentum['score']}")
        print(f"   Объём: Score {volume['score']}")
        print(f"   Волатильность: {volatility['atr_percent']:.2f}% (Score: {volatility['score']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


async def test_database():
    """Тест подключения к БД"""
    print("\n💾 Тестирование базы данных...")
    
    try:
        from database.models import get_db, Signal
        
        db = get_db()
        
        # Попытка запроса
        count = db.query(Signal).count()
        print(f"✅ Подключение к БД успешно")
        print(f"   Сигналов в базе: {count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("\n   Убедитесь что:")
        print("   1. PostgreSQL запущен")
        print("   2. База данных 'crypto_signals' создана")
        print("   3. Параметры в .env правильные")
        return False


async def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ КРИПТО-СИГНАЛЬНОГО БОТА")
    print("=" * 60)
    
    tests = [
        ("База данных", test_database),
        ("Подключение к бирже", test_exchange_connection),
        ("Технический анализ", test_technical_analysis),
        ("Генерация сигналов", test_signal_generation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Критическая ошибка в тесте '{name}': {e}")
            results.append((name, False))
        
        print()
    
    # Итоги
    print("=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! Бот готов к запуску.")
        print("\nЗапустите основного бота командой:")
        print("   python main.py")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте конфигурацию.")
        print("\nСмотрите:")
        print("   - SETUP.md для инструкций по настройке")
        print("   - .env для проверки параметров")
        print("   - logs/ для подробных логов")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹ Тестирование прервано")

