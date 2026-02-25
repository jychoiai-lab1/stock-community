import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')
import os
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

# =============================================
# 설정
# =============================================
SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMjIxNDYsImV4cCI6MjA4NzU5ODE0Nn0.oBwDXc1x4II1M4NX5AcfXIt2MTx4L3m4e9mHwqo-ObA'

MARKET_TICKERS = {
    'NDX (나스닥100)': '^NDX',
    'SPX (S&P500)':   '^GSPC',
    'VIX (공포지수)':  '^VIX',
    'USD/JPY':         'USDJPY=X',
    'BTC/USDT':        'BTC-USD',
}

# 기술적 분석 대상 종목 (여기에 추가/수정하세요)
ANALYSIS_TICKERS = {
    'URA (우라늄 ETF)': 'URA',
}

CHART_DIR = 'C:/Users/asdf/webtest/charts'
os.makedirs(CHART_DIR, exist_ok=True)

# =============================================
# 기술적 지표
# =============================================
def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_macd(series):
    ema12 = calc_ema(series, 12)
    ema26 = calc_ema(series, 26)
    macd = ema12 - ema26
    signal = calc_ema(macd, 9)
    hist = macd - signal
    return macd, signal, hist

def check_divergence(price, macd_hist, n=5):
    p = price.iloc[-n:]
    m = macd_hist.iloc[-n:]
    if p.iloc[-1] < p.iloc[0] and m.iloc[-1] > m.iloc[0]:
        return "📈 상승 다이버전스 감지"
    if p.iloc[-1] > p.iloc[0] and m.iloc[-1] < m.iloc[0]:
        return "📉 하락 다이버전스 감지"
    return None

def check_ema_cross(close):
    signals = []
    periods = [7, 20, 50, 100, 200]
    emas = {p: calc_ema(close, p) for p in periods}
    for fast, slow in [(7,20),(20,50),(50,100),(50,200),(100,200)]:
        prev_diff = emas[fast].iloc[-2] - emas[slow].iloc[-2]
        curr_diff = emas[fast].iloc[-1] - emas[slow].iloc[-1]
        if prev_diff > 0 and curr_diff <= 0:
            signals.append(f"  ⚠️ 데드크로스 EMA{fast}/EMA{slow}")
        elif prev_diff < 0 and curr_diff >= 0:
            signals.append(f"  ✅ 골든크로스 EMA{fast}/EMA{slow}")
    return signals

# =============================================
# 차트 생성 및 Supabase 업로드
# =============================================
def generate_chart(ticker, name, client):
    try:
        data = yf.download(ticker, period='3mo', interval='1d', progress=False, auto_adjust=True)
        if len(data) < 10:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.index = pd.to_datetime(data.index)
        data = data[['Open','High','Low','Close','Volume']].dropna()

        ema20 = calc_ema(data['Close'], 20)
        ema50 = calc_ema(data['Close'], 50)
        apds = [
            mpf.make_addplot(ema20, color='#3182f6', width=1.2),
            mpf.make_addplot(ema50, color='#f04452', width=1.2),
        ]

        safe_name = ticker.replace('^','').replace('=','')
        fname = f"{CHART_DIR}/{safe_name}.png"
        mpf.plot(
            data,
            type='candle',
            style='yahoo',
            title=f'{name} - 일봉 (3개월)',
            addplot=apds,
            volume=True,
            savefig=dict(fname=fname, dpi=120, bbox_inches='tight'),
            figsize=(10, 6),
        )

        storage_path = f"{safe_name}.png"
        with open(fname, 'rb') as f:
            img_data = f.read()
        client.storage.from_('chart').upload(
            storage_path, img_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/chart/{storage_path}"
        print(f"    차트 업로드 완료: {name}")
        return public_url

    except Exception as e:
        print(f"    차트 오류 ({name}): {e}")
        return None

# =============================================
# 시장 등락률
# =============================================
def get_market_overview():
    lines = []
    for name, ticker in MARKET_TICKERS.items():
        try:
            data = yf.download(ticker, period='2d', interval='1d', progress=False, auto_adjust=True)
            if len(data) < 2:
                lines.append(f"  {name}: 데이터 없음")
                continue
            close = data['Close'].squeeze()
            prev = float(close.iloc[-2])
            curr = float(close.iloc[-1])
            chg = ((curr - prev) / prev) * 100
            arrow = "▲" if chg >= 0 else "▼"
            sign = "+" if chg >= 0 else ""
            lines.append(f"  {name}: {curr:,.2f}  {arrow} {sign}{chg:.2f}%")
        except Exception as e:
            lines.append(f"  {name}: 오류({e})")
    return "\n".join(lines)

# =============================================
# 기술적 분석
# =============================================
def analyze_ticker(name, ticker):
    try:
        data = yf.download(ticker, period='1y', interval='1d', progress=False, auto_adjust=True)
        if len(data) < 200:
            return f"\n[ {name} ({ticker}) ]\n  데이터 부족\n"
        close = data['Close'].squeeze()
        volume = data['Volume'].squeeze()
        periods = [7, 20, 50, 100, 200]
        emas = {p: calc_ema(close, p) for p in periods}
        ema_lines = "  EMA: " + " | ".join([f"EMA{p}={float(emas[p].iloc[-1]):,.2f}" for p in periods])
        cross_signals = check_ema_cross(close)
        cross_text = "\n".join(cross_signals) if cross_signals else "  크로스 신호 없음"
        rsi = calc_rsi(close)
        rsi_val = float(rsi.iloc[-1])
        rsi_comment = "과매수 구간" if rsi_val >= 70 else ("과매도 구간" if rsi_val <= 30 else "중립")
        macd, signal, hist = calc_macd(close)
        div = check_divergence(close, hist)
        avg_vol = float(volume.iloc[-20:].mean())
        curr_vol = float(volume.iloc[-1])
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1
        if vol_ratio >= 1.5:
            vol_comment = f"🔥 급증 ({vol_ratio:.1f}x)"
        elif vol_ratio >= 1.1:
            vol_comment = f"↑ 증가 ({vol_ratio:.1f}x)"
        elif vol_ratio <= 0.7:
            vol_comment = f"↓ 감소 ({vol_ratio:.1f}x)"
        else:
            vol_comment = f"보통 ({vol_ratio:.1f}x)"
        prev_close = float(close.iloc[-2])
        curr_close = float(close.iloc[-1])
        chg = ((curr_close - prev_close) / prev_close) * 100
        sign = "+" if chg >= 0 else ""
        return (
            f"\n[ {name} ({ticker}) ]\n"
            f"  현재가: {curr_close:,.2f}  ({sign}{chg:.2f}%)\n"
            f"{ema_lines}\n"
            f"{cross_text}\n"
            f"  RSI(14): {rsi_val:.1f}  → {rsi_comment}\n"
            f"  MACD: {float(macd.iloc[-1]):.3f} / Signal: {float(signal.iloc[-1]):.3f}\n"
            f"  다이버전스: {div if div else '없음'}\n"
            f"  거래량: {vol_comment}\n"
        )
    except Exception as e:
        return f"\n[ {name} ({ticker}) ]\n  분석 오류: {e}\n"

# =============================================
# Supabase 게시글 업로드
# =============================================
def post_to_supabase(client, title, content):
    client.table('posts').insert({
        'category': '📊 아침 브리핑',
        'title': title,
        'content': content,
        'views': 0
    }).execute()

# =============================================
# 메인
# =============================================
def main():
    today = datetime.now().strftime('%Y년 %m월 %d일')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 브리핑 생성 시작...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  시장 데이터 수집 중...")
    market = get_market_overview()

    print("  차트 생성 중...")
    chart_html = ""
    for name, ticker in MARKET_TICKERS.items():
        url = generate_chart(ticker, name, client)
        if url:
            chart_html += f'<div class="chart-block"><p class="chart-label">{name}</p><img src="{url}" class="chart-img"/></div>\n'

    analysis_parts = []
    for name, ticker in ANALYSIS_TICKERS.items():
        print(f"  {name} 분석 중...")
        analysis_parts.append(analyze_ticker(name, ticker))
    analysis = "\n".join(analysis_parts)

    title = f"{today} 아침 주식 브리핑"
    content = (
        '<div class="briefing">'
        '<h3>🌍 주요 시장 현황</h3>'
        f'<pre>{market}</pre>'
        '<h3>📈 지수 차트 (일봉)</h3>'
        f'<div class="chart-grid">{chart_html}</div>'
        '<h3>🔬 기술적 분석</h3>'
        f'<pre>{analysis}</pre>'
        f'<p class="auto-time">⏰ 자동 생성: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>'
        '</div>'
    )

    # 오늘 날짜 게시물 삭제 (중복 방지)
    today_start = datetime.now().strftime('%Y-%m-%d') + 'T00:00:00'
    old = client.table('posts').select('id').gte('created_at', today_start).execute()
    if old.data:
        ids = [p['id'] for p in old.data]
        client.table('posts').delete().in_('id', ids).execute()
        print(f"  기존 오늘 게시물 {len(ids)}개 삭제")

    print("  Supabase 업로드 중...")
    post_to_supabase(client, title, content)
    print(f"[완료] '{title}' 업로드 완료!")

if __name__ == '__main__':
    main()
