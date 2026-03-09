import yfinance as yf
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

SECTORS = {
    'XLK':  '기술',
    'XLC':  '커뮤니케이션',
    'XLY':  '소비재(경기)',
    'XLF':  '금융',
    'XLI':  '산업재',
    'XLV':  '헬스케어',
    'XLP':  '필수소비재',
    'XLB':  '소재',
    'XLE':  '에너지',
    'XLRE': '부동산',
    'XLU':  '유틸리티',
}

def calc_pct(close, idx_from_end):
    n = len(close)
    if n < idx_from_end + 1:
        return 0.0
    curr = float(close.iloc[-1])
    prev = float(close.iloc[-(idx_from_end + 1)])
    if prev == 0:
        return 0.0
    return round((curr - prev) / prev * 100, 2)

def update_sectors(client):
    now = datetime.utcnow().isoformat()
    for etf, name in SECTORS.items():
        try:
            data = yf.download(etf, period='2y', interval='1d', progress=False, auto_adjust=True)
            if data.empty or len(data) < 5:
                print(f"  {name} ({etf}): 데이터 부족")
                continue

            close = data['Close'].squeeze()
            day_pct   = calc_pct(close, 1)
            week_pct  = calc_pct(close, 5)
            month_pct = calc_pct(close, 21)
            year_pct  = calc_pct(close, 252)

            row = {
                'ticker':     etf,
                'name':       name,
                'day_pct':    day_pct,
                'week_pct':   week_pct,
                'month_pct':  month_pct,
                'year_pct':   year_pct,
                'updated_at': now,
            }
            client.table('sector_performance').upsert(row, on_conflict='ticker').execute()
            arrow = '▲' if day_pct >= 0 else '▼'
            print(f"  {name:12s} ({etf:4s}): {arrow} {day_pct:+.2f}%  1W {week_pct:+.2f}%  1M {month_pct:+.2f}%  1Y {year_pct:+.2f}%")
        except Exception as e:
            print(f"  {etf} 오류: {e}")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 섹터 퍼포먼스 업데이트 중...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    update_sectors(client)
    print("완료!")
