import yfinance as yf
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

def vix_to_score(vix):
    # VIX 10 = 100(극도의 탐욕), VIX 40 = 0(극도의 공포)
    score = int((40 - vix) / 30 * 100)
    return max(0, min(100, score))

def update_fear_greed(client):
    data = yf.download('^VIX', period='2d', interval='1d', progress=False, auto_adjust=True)
    if data.empty:
        print("  VIX 데이터 없음")
        return
    vix = float(data['Close'].squeeze().iloc[-1])
    score = vix_to_score(vix)

    label_map = [
        (20, '극도의 공포'),
        (40, '공포'),
        (60, '중립'),
        (80, '탐욕'),
        (101, '극도의 탐욕'),
    ]
    label = next(l for threshold, l in label_map if score < threshold)

    client.table('fear_greed').update({
        'value': score,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', 1).execute()

    print(f"  VIX {vix:.2f} -> score {score} ({label})")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fear & Greed updating...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    update_fear_greed(client)
    print("Done!")
