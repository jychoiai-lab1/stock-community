import yfinance as yf
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

# symbol_key: (yf_ticker, 표시명, 표시_unit)
TICKER_SYMBOLS = {
    'SPX':    ('^GSPC',    'S&P 500',    ''),
    'NDX':    ('^NDX',     'NASDAQ',     ''),
    'DJI':    ('^DJI',     'DOW',        ''),
    'VIX':    ('^VIX',     'VIX',        ''),
    'DXY':    ('DX=F',     'DXY',        ''),
    'TNX':    ('^TNX',     '10Y 금리',   '%'),
    'BTC':    ('BTC-USD',  'BTC',        ''),
    'GOLD':   ('GC=F',     'GOLD',       ''),
    'OIL':    ('CL=F',     'WTI',        ''),
    'USDJPY': ('USDJPY=X', 'USD/JPY',    ''),
}

def update_tickers(client):
    for key, (ticker, name, unit) in TICKER_SYMBOLS.items():
        try:
            data = yf.download(ticker, period='5d', interval='1d', progress=False, auto_adjust=True)
            if len(data) < 2:
                print(f"  {name}: 데이터 부족")
                continue
            close = data['Close'].squeeze()
            prev = float(close.iloc[-2])
            curr = float(close.iloc[-1])
            chg = ((curr - prev) / prev) * 100
            sign = '+' if chg >= 0 else ''

            # 소수점 자리수 결정
            if key in ('VIX', 'TNX', 'DXY', 'USDJPY'):
                price_str = f'{curr:.2f}'
            elif key == 'BTC':
                price_str = f'{curr:,.0f}'
            elif key in ('GOLD', 'OIL'):
                price_str = f'{curr:.2f}'
            else:
                price_str = f'{curr:,.2f}'

            row = {
                'symbol_key': key,
                'name':       name,
                'price':      price_str + (unit if unit else ''),
                'change_pct': f'{sign}{chg:.2f}%',
                'is_up':      chg >= 0,
            }
            existing = client.table('market_ticker').select('id').eq('symbol_key', key).execute()
            if existing.data:
                client.table('market_ticker').update(row).eq('symbol_key', key).execute()
            else:
                client.table('market_ticker').insert(row).execute()

            arrow = '▲' if chg >= 0 else '▼'
            print(f'  {name:10s}: {price_str:>12s}  {arrow} {sign}{chg:.2f}%')
        except Exception as e:
            print(f'  {name} 오류: {e}')

if __name__ == '__main__':
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 티커 업데이트 중...')
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    update_tickers(client)
    print('완료!')
