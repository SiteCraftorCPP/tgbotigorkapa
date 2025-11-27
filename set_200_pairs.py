"""
Скрипт для установки 200 торговых пар
Запустить один раз для инициализации пар в базе данных
"""

from database.models import init_db
from database.config_manager import ConfigManager

# Список 200 торговых пар (убраны некорректные: USDT/USDT и т.п.)
TRADING_PAIRS_200 = [
    # Major coins
    "BTC/USDT", "ETH/USDT", "XRP/USDT", "BNB/USDT", "SOL/USDT", "TRX/USDT",
    "DOGE/USDT", "ADA/USDT", "BCH/USDT", "LINK/USDT", "ZEC/USDT", "XLM/USDT",
    "XMR/USDT", "LTC/USDT", "AVAX/USDT", "HBAR/USDT", "SUI/USDT", "SHIB/USDT",
    "CRO/USDT", "TON/USDT", "UNI/USDT", "DOT/USDT", "MNT/USDT", "TAO/USDT",
    "AAVE/USDT", "NEAR/USDT", "OKB/USDT", "ICP/USDT", "ETC/USDT", "PI/USDT",
    "ENA/USDT", "PEPE/USDT", "APT/USDT", "KAS/USDT", "ONDO/USDT", "WLD/USDT",
    "KCS/USDT", "POL/USDT", "ALGO/USDT", "TRUMP/USDT", "ARB/USDT", "ATOM/USDT",
    "VET/USDT", "FIL/USDT", "FLR/USDT", "QNT/USDT", "XDC/USDT", "RENDER/USDT",
    "SEI/USDT", "IP/USDT", "GT/USDT", "CAKE/USDT", "BONK/USDT", "JUP/USDT",
    "DASH/USDT", "PENGU/USDT", "SPX/USDT", "STRK/USDT", "VIRTUAL/USDT",
    "IMX/USDT", "AERO/USDT", "NEXO/USDT", "FET/USDT", "OP/USDT", "CRV/USDT",
    "INJ/USDT", "LDO/USDT", "STX/USDT", "TIA/USDT", "MORPHO/USDT", "GRT/USDT",
    "XTZ/USDT", "KAIA/USDT", "IOTA/USDT", "ETHFI/USDT", "FLOKI/USDT",
    "TWT/USDT", "PENDLE/USDT", "PYTH/USDT", "ENS/USDT", "MON/USDT", "CFX/USDT",
    "DCR/USDT", "SAND/USDT", "BSV/USDT", "HNT/USDT", "BTT/USDT", "SUN/USDT",
    "DEXE/USDT", "JST/USDT", "FLOW/USDT", "WIF/USDT", "GALA/USDT", "ZK/USDT",
    "GNO/USDT", "FARTCOIN/USDT", "BAT/USDT", "MANA/USDT", "ZRO/USDT",
    "RAY/USDT", "NEO/USDT", "TRAC/USDT", "COMP/USDT", "CHZ/USDT", "EIGEN/USDT",
    "AR/USDT", "1INCH/USDT", "WAL/USDT", "ATH/USDT", "XEC/USDT", "GLM/USDT",
    "FLUID/USDT", "EGLD/USDT", "RUNE/USDT", "ZEN/USDT", "DEEP/USDT",
    "RSR/USDT", "JTO/USDT", "SNX/USDT", "APE/USDT", "FTT/USDT", "DYDX/USDT",
    "MX/USDT", "KMNO/USDT", "XCN/USDT", "AXS/USDT", "LPT/USDT", "AMP/USDT",
    "CVX/USDT", "BRETT/USDT", "BEAM/USDT", "TOSHI/USDT", "KAITO/USDT",
    "SFP/USDT", "QTUM/USDT", "SUPER/USDT", "CTC/USDT", "PROM/USDT",
    "KSM/USDT", "LUNC/USDT", "FORM/USDT", "AIOZ/USDT", "MOVE/USDT",
    "TFUEL/USDT", "AKT/USDT", "GAS/USDT", "CORE/USDT", "AXL/USDT", "YFI/USDT",
    "FTN/USDT", "BDX/USDT", "BORG/USDT", "MINA/USDT", "DOG/USDT", "BERA/USDT",
    "ZRX/USDT", "RON/USDT", "KAVA/USDT", "SHFL/USDT", "BABYDOGE/USDT",
    "RVN/USDT", "CKB/USDT", "MELANIA/USDT", "DGB/USDT", "XNO/USDT",
    "MOG/USDT", "XVG/USDT", "GOMINING/USDT", "VELO/USDT", "ALEO/USDT",
    "ZIL/USDT", "SNEK/USDT", "BIO/USDT", "SUSHI/USDT", "ROSE/USDT",
    "TURBO/USDT", "MEW/USDT", "ASTR/USDT", "SAFE/USDT", "ORCA/USDT",
    "POPCAT/USDT", "QUBIC/USDT", "HYPE/USDT", "LEO/USDT", "WLFI/USDT",
    "CC/USDT", "ASTER/USDT", "BGB/USDT", "XAUT/USDT", "PAXG/USDT",
    "SKY/USDT", "PUMP/USDT", "FDUSD/USDT", "MYX/USDT", "AB/USDT",
    "TEL/USDT", "USDD/USDT", "2Z/USDT", "NFT/USDT", "XPL/USDT",
    "SYRUP/USDT", "EURC/USDT", "A/USDT", "S/USDT", "MERL/USDT", "FF/USDT",
    "ZBCN/USDT", "H/USDT", "VSN/USDT", "0G/USDT", "ZORA/USDT", "W/USDT"
]


def main():
    print("=" * 60)
    print("УСТАНОВКА 200 ТОРГОВЫХ ПАР")
    print("=" * 60)
    
    # Инициализация БД
    init_db()
    
    # Фильтруем дубликаты и пустые значения
    pairs = list(dict.fromkeys([p.strip() for p in TRADING_PAIRS_200 if p.strip()]))
    
    print(f"\nВсего пар для установки: {len(pairs)}")
    print(f"Первые 10: {', '.join(pairs[:10])}")
    print(f"Последние 10: {', '.join(pairs[-10:])}")
    
    # Устанавливаем пары
    success = ConfigManager.set_trading_pairs(pairs)
    
    if success:
        print(f"\n✅ Успешно установлено {len(pairs)} торговых пар!")
        
        # Проверяем
        saved_pairs = ConfigManager.get_trading_pairs()
        print(f"Проверка: загружено {len(saved_pairs)} пар из БД")
    else:
        print("\n❌ Ошибка при установке торговых пар!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

