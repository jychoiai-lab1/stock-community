import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from datetime import datetime
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정 (Windows 맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

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
            title=f'{ticker.replace("^","").replace("=","")} - Daily Chart (3M)',
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
# 기술적 분석 (HTML 반환)
# =============================================
def analyze_ticker_html(name, ticker):
    try:
        data = yf.download(ticker, period='1y', interval='1d', progress=False, auto_adjust=True)
        if len(data) < 50:
            return '<p class="an-error">데이터 부족</p>'

        close = data['Close'].squeeze()
        has_volume = 'Volume' in data.columns and data['Volume'].squeeze().sum() > 0
        volume = data['Volume'].squeeze() if has_volume else None

        # 현재가 / 등락률
        prev_close = float(close.iloc[-2])
        curr_close = float(close.iloc[-1])
        chg = ((curr_close - prev_close) / prev_close) * 100
        sign = "+" if chg >= 0 else ""
        chg_class = "up" if chg >= 0 else "down"
        arrow = "▲" if chg >= 0 else "▼"

        # EMA
        periods = [7, 20, 50, 100, 200]
        avail = [p for p in periods if len(close) >= p]
        emas = {p: calc_ema(close, p) for p in avail}
        ema_items = "".join([
            f'<span class="ema-item">EMA{p}<b>{float(emas[p].iloc[-1]):,.2f}</b></span>'
            for p in avail
        ])

        # EMA 크로스
        cross_signals = check_ema_cross(close) if len(close) >= 200 else []
        if cross_signals:
            cross_html = "".join([f'<div class="signal-badge {"dead" if "데드" in s else "golden"}">{s.strip()}</div>' for s in cross_signals])
        else:
            cross_html = '<span class="an-neutral">크로스 신호 없음</span>'

        # RSI
        rsi_val = float(calc_rsi(close).iloc[-1])
        if rsi_val >= 70:
            rsi_class, rsi_comment = "up", "과매수 구간 ⚠️"
        elif rsi_val <= 30:
            rsi_class, rsi_comment = "down", "과매도 구간 💡"
        else:
            rsi_class, rsi_comment = "neutral", "중립"

        # MACD
        macd_line, sig_line, hist_line = calc_macd(close)
        macd_val = float(macd_line.iloc[-1])
        sig_val = float(sig_line.iloc[-1])
        div = check_divergence(close, hist_line)
        macd_trend = "상승세" if macd_val > sig_val else "하락세"
        macd_class = "up" if macd_val > sig_val else "down"

        # 거래량
        if volume is not None:
            avg_vol = float(volume.iloc[-20:].mean())
            curr_vol = float(volume.iloc[-1])
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1
            if vol_ratio >= 1.5:
                vol_html = f'<span class="up">🔥 급증 ({vol_ratio:.1f}x 평균 대비)</span>'
            elif vol_ratio >= 1.1:
                vol_html = f'<span class="up">↑ 증가 ({vol_ratio:.1f}x)</span>'
            elif vol_ratio <= 0.7:
                vol_html = f'<span class="down">↓ 감소 ({vol_ratio:.1f}x)</span>'
            else:
                vol_html = f'<span class="neutral">보통 ({vol_ratio:.1f}x)</span>'
        else:
            vol_html = '<span class="neutral">N/A</span>'

        # 종합 의견
        bullish = sum([chg > 0, rsi_val < 60, macd_val > sig_val])
        if bullish >= 2:
            opinion = "단기 강세 흐름. 추세 유지 여부 확인 필요."
            op_class = "up"
        else:
            opinion = "단기 약세 흐름. 지지선 확인 후 진입 고려."
            op_class = "down"

        return f'''
<div class="an-price">
  <span class="an-curr {chg_class}">{curr_close:,.2f}</span>
  <span class="an-chg {chg_class}">{arrow} {sign}{chg:.2f}%</span>
</div>
<div class="an-section">
  <div class="an-label">📊 EMA</div>
  <div class="ema-row">{ema_items}</div>
  <div class="an-label" style="margin-top:8px">크로스 신호</div>
  {cross_html}
</div>
<div class="an-section">
  <div class="an-label">📈 RSI (14)</div>
  <div class="an-row">
    <div class="rsi-bar-wrap"><div class="rsi-bar" style="width:{min(rsi_val,100):.0f}%"></div></div>
    <span class="{rsi_class}">{rsi_val:.1f} — {rsi_comment}</span>
  </div>
</div>
<div class="an-section">
  <div class="an-label">📉 MACD</div>
  <div class="an-row">
    <span>MACD <b>{macd_val:.3f}</b></span>
    <span>Signal <b>{sig_val:.3f}</b></span>
    <span class="{macd_class}">{macd_trend}</span>
  </div>
  <div class="an-div">{div if div else "다이버전스 없음"}</div>
</div>
<div class="an-section">
  <div class="an-label">📦 거래량</div>
  {vol_html}
</div>
<div class="an-opinion {op_class}">💬 {opinion}</div>'''

    except Exception as e:
        return f'<p class="an-error">분석 오류: {e}</p>'

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

    print("  차트 및 분석 생성 중...")
    market_sections = ""
    for name, ticker in MARKET_TICKERS.items():
        print(f"    {name} 처리 중...")
        url = generate_chart(ticker, name, client)
        analysis_html = analyze_ticker_html(name, ticker)
        img_tag = f'<img src="{url}" class="chart-img-full"/>' if url else '<p class="an-error">차트 생성 실패</p>'
        market_sections += f'''
<div class="ticker-section">
  <h3 class="ticker-title">{name}</h3>
  {img_tag}
  <div class="analysis-box">
    {analysis_html}
  </div>
</div>'''

    special_sections = ""
    for name, ticker in ANALYSIS_TICKERS.items():
        print(f"    {name} 특별분석 중...")
        url = generate_chart(ticker, name, client)
        analysis_html = analyze_ticker_html(name, ticker)
        img_tag = f'<img src="{url}" class="chart-img-full"/>' if url else '<p class="an-error">차트 생성 실패</p>'
        special_sections += f'''
<div class="ticker-section special">
  <h3 class="ticker-title">⭐ {name} — 오늘의 특별 분석</h3>
  {img_tag}
  <div class="analysis-box">
    {analysis_html}
  </div>
</div>'''

    title = f"{today} 아침 주식 브리핑"
    content = (
        '<div class="briefing">'
        '<h3>🌍 주요 시장 현황</h3>'
        f'<pre>{market}</pre>'
        '<h3>📈 지수별 차트 & 분석</h3>'
        f'{market_sections}'
        + (f'<h3>🔬 특별 종목 분석</h3>{special_sections}' if special_sections else '')
        + f'<p class="auto-time">⏰ 자동 생성: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>'
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
