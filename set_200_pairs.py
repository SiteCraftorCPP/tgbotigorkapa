"""
Скрипт для установки 200 торговых пар
Запустить один раз для инициализации пар в базе данных
"""

from database.models import init_db
from database.config_manager import ConfigManager

# Список 200 торговых пар (убраны некорректные: USDT/USDT)
TRADING_PAIRS_200 = [
    "BTC/USDT", "ETH/USDT", "XRP/USDT", "BNB/USDT", "SOL/USDT", "USDC/USDT",
    "TRX/USDT", "DOGE/USDT", "ADA/USDT", "HYPE/USDT", "BCH/USDT", "LINK/USDT",
    "LEO/USDT", "ZEC/USDT", "XLM/USDT", "XMR/USDT", "USDE/USDT", "LTC/USDT",
    "AVAX/USDT", "HBAR/USDT", "SUI/USDT", "DAI/USDT", "SHIB/USDT", "WLFI/USDT",
    "CRO/USDT", "TON/USDT", "UNI/USDT", "DOT/USDT", "PYUSD/USDT", "MNT/USDT",
    "TAO/USDT", "CC/USDT", "AAVE/USDT", "USD1/USDT", "ASTER/USDT", "BGB/USDT",
    "NEAR/USDT", "OKB/USDT", "ICP/USDT", "ETC/USDT", "PI/USDT", "ENA/USDT",
    "PEPE/USDT", "APT/USDT", "KAS/USDT", "ONDO/USDT", "XAUT/USDT", "WLD/USDT",
    "KCS/USDT", "POL/USDT", "PAXG/USDT", "M/USDT", "ALGO/USDT", "TRUMP/USDT",
    "ARB/USDT", "USDG/USDT", "ATOM/USDT", "VET/USDT", "FIL/USDT", "FLR/USDT",
    "SKY/USDT", "PUMP/USDT", "RLUSD/USDT", "QNT/USDT", "XDC/USDT", "RENDER/USDT",
    "FDUSD/USDT", "SEI/USDT", "IP/USDT", "GT/USDT", "CAKE/USDT", "BONK/USDT",
    "JUP/USDT", "DASH/USDT", "PENGU/USDT", "SPX/USDT", "STRK/USDT", "VIRTUAL/USDT",
    "IMX/USDT", "AERO/USDT", "NEXO/USDT", "FET/USDT", "OP/USDT", "CRV/USDT",
    "INJ/USDT", "LDO/USDT", "STX/USDT", "MYX/USDT", "AB/USDT", "TIA/USDT",
    "MORPHO/USDT", "GRT/USDT", "XTZ/USDT", "KAIA/USDT", "TUSD/USDT", "IOTA/USDT",
    "ETHFI/USDT", "FLOKI/USDT", "USDD/USDT", "TEL/USDT", "TWT/USDT", "PENDLE/USDT",
    "PYTH/USDT", "ENS/USDT", "MON/USDT", "2Z/USDT", "CFX/USDT", "DCR/USDT",
    "SAND/USDT", "BSV/USDT", "HNT/USDT", "BTT/USDT", "SUN/USDT", "NFT/USDT",
    "DEXE/USDT", "XPL/USDT", "JST/USDT", "FLOW/USDT", "WIF/USDT", "GALA/USDT",
    "ZK/USDT", "GNO/USDT", "FARTCOIN/USDT", "SYRUP/USDT", "BAT/USDT", "EURC/USDT",
    "MANA/USDT", "A/USDT", "ZRO/USDT", "S/USDT", "RAY/USDT", "MERL/USDT",
    "FF/USDT", "NEO/USDT", "ZBCN/USDT", "TRAC/USDT", "COMP/USDT", "CHZ/USDT",
    "H/USDT", "EIGEN/USDT", "AR/USDT", "VSN/USDT", "1INCH/USDT", "0G/USDT",
    "WAL/USDT", "ZORA/USDT", "ATH/USDT", "XEC/USDT", "GLM/USDT", "FLUID/USDT",
    "W/USDT", "EGLD/USDT", "RUNE/USDT", "ZEN/USDT", "DEEP/USDT", "RSR/USDT",
    "JTO/USDT", "CHEEMS/USDT", "SNX/USDT", "APE/USDT", "FTT/USDT", "DYDX/USDT",
    "MX/USDT", "KMNO/USDT", "XCN/USDT", "SAHARA/USDT", "WEMIX/USDT", "KITE/USDT",
    "AXS/USDT", "LPT/USDT", "AMP/USDT", "CVX/USDT", "BRETT/USDT", "BEAM/USDT",
    "TOSHI/USDT", "KAITO/USDT", "MET/USDT", "SFP/USDT", "QTUM/USDT", "LINEA/USDT",
    "B/USDT", "BARD/USDT", "SOON/USDT", "SUPER/USDT", "CTC/USDT", "PROM/USDT",
    "KSM/USDT", "LUNC/USDT", "FORM/USDT", "AIOZ/USDT", "MOVE/USDT", "TFUEL/USDT",
    "AKT/USDT", "GAS/USDT", "CORE/USDT", "AXL/USDT", "YFI/USDT", "USDF/USDT",
    "JLP/USDT", "USDf/USDT", "RAIN/USDT", "USDY/USDT", "FTN/USDT", "BDX/USDT",
    "USD0/USDT", "USDAI/USDT", "GHO/USDT", "ZBU/USDT", "BORG/USDT", "FRAX/USDT",
    "LION/USDT", "UDS/USDT", "ZANO/USDT", "TIBBIR/USDT", "CCD/USDT", "ALE/USDT",
    "LGCT/USDT", "SOSO/USDT", "WFI/USDT", "DUSD/USDT", "KOGE/USDT", "BMX/USDT",
    "GUSD/USDT", "MINA/USDT", "DOG/USDT", "BERA/USDT", "ZRX/USDT", "UPC/USDT",
    "RON/USDT", "KAVA/USDT", "SHFL/USDT", "BABYDOGE/USDT", "RVN/USDT", "AUSD/USDT",
    "KTA/USDT", "CKB/USDT", "MELANIA/USDT", "T/USDT", "SLT/USDT", "FLZ/USDT",
    "DGB/USDT", "XNO/USDT", "MOG/USDT", "XVG/USDT", "GOMINING/USDT", "NPC/USDT",
    "USELESS/USDT", "VELO/USDT", "ALEO/USDT", "ZIL/USDT", "BEAT/USDT", "GIGGLE/USDT",
    "SNEK/USDT", "BIO/USDT", "ULTIMA/USDT", "SUSHI/USDT", "ESPORTS/USDT", "ROSE/USDT",
    "REAL/USDT", "XPR/USDT", "YZY/USDT", "TURBO/USDT", "MEW/USDT", "FRXUSD/USDT",
    "FOLKS/USDT", "UB/USDT", "ASTR/USDT", "SAFE/USDT", "AVNT/USDT", "ORCA/USDT",
    "POPCAT/USDT", "QUBIC/USDT", "VCNT/USDT"
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
        
        if len(saved_pairs) != len(pairs):
            print(f"⚠️  Внимание: сохранено {len(saved_pairs)} пар, ожидалось {len(pairs)}")
    else:
        print("\n❌ Ошибка при установке торговых пар!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
