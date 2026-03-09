import yfinance as yf
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

def upsert(client, key, value, label, unit=''):
    now = datetime.utcnow().isoformat()
    client.table('macro_indicators').upsert({
        'key': key,
        'value': value,
        'label': label,
        'unit': unit,
        'updated_at': now,
    }, on_conflict='key').execute()

def update_macro(client):
    # S&P500 PER (SPY trailing PE 사용)
    try:
        info = yf.Ticker('SPY').info
        pe = info.get('trailingPE')
        if pe:
            upsert(client, 'sp500_pe', round(pe, 1), 'S&P500 PER', 'x')
            print(f"  S&P500 PER: {pe:.1f}x")
    except Exception as e:
        print(f"  PER 오류: {e}")

    # 국채 금리
    yields = {
        'treasury_2y':  ('^IRX', '2년 국채금리', '%'),
        'treasury_10y': ('^TNX', '10년 국채금리', '%'),
        'treasury_30y': ('^TYX', '30년 국채금리', '%'),
    }
    for key, (ticker, label, unit) in yields.items():
        try:
            data = yf.download(ticker, period='5d', interval='1d', progress=False, auto_adjust=True)
            if not data.empty:
                val = round(float(data['Close'].squeeze().iloc[-1]), 3)
                upsert(client, key, val, label, unit)
                print(f"  {label}: {val:.3f}%")
        except Exception as e:
            print(f"  {label} 오류: {e}")

    # S&P500 시가총액 / GDP 비율 — Buffett Indicator (근사값, 수동)
    # Fed 기준금리는 자동화 어려움 — 별도 수동 업데이트
    # VIX (변동성 지수)
    try:
        data = yf.download('^VIX', period='5d', interval='1d', progress=False, auto_adjust=True)
        if not data.empty:
            val = round(float(data['Close'].squeeze().iloc[-1]), 2)
            upsert(client, 'vix', val, 'VIX 변동성', '')
            print(f"  VIX: {val:.2f}")
    except Exception as e:
        print(f"  VIX 오류: {e}")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 매크로 지표 업데이트 중...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    update_macro(client)
    print("완료!")
