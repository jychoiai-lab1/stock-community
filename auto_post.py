import yfinance as yf
import pandas as pd
from datetime import datetime
from supabase import create_client
import warnings
import os
from docx import Document
warnings.filterwarnings('ignore')

REPORTS_DIR = r'C:\Users\asdf\webtest\reports'

def read_report(ticker):
    """종목 코드로 docx 파일 읽기 — CHART_KEYS 단축키 우선 (예: SKT.docx)"""
    key = CHART_KEYS.get(ticker, ticker.replace('^','').replace('=X','').replace('.KS',''))
    for name in [key, ticker]:
        path = os.path.join(REPORTS_DIR, f'{name}.docx')
        if os.path.exists(path):
            break
    else:
        return None
    try:
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n'.join(paragraphs)
    except Exception as e:
        print(f"  보고서 읽기 오류 ({ticker}): {e}")
        return None

def report_to_html(text):
    """보고서 텍스트를 HTML로 변환"""
    lines = text.split('\n')
    html = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('# '):
            html += f'<h4 style="color:#f1f5f9;margin:16px 0 8px;">{line[2:]}</h4>'
        elif line.startswith('## '):
            html += f'<h5 style="color:#94a3b8;margin:12px 0 6px;">{line[3:]}</h5>'
        else:
            html += f'<p style="font-size:14px;color:#cbd5e1;line-height:1.8;margin:4px 0;">{line}</p>'
    return html

# =============================================
# 설정
# =============================================
SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

MARKET_TICKERS = {
    'NDX (나스닥100)': '^NDX',
    'SPX (S&P500)':   '^GSPC',
    'VIX (공포지수)':  '^VIX',
    'USD/JPY':         'USDJPY=X',
    'DXY (달러인덱스)': 'DX=F',
    'BTC/USDT':        'BTC-USD',
}

# 기술적 분석 대상 종목 (여기에 추가/수정하세요)
ANALYSIS_TICKERS = {
    'Apollo Global Management, Inc.': 'APO',
}

# yfinance 티커 → chart_data 키 매핑
CHART_KEYS = {
    '^NDX':     'NDX',
    '^GSPC':    'SPX',
    '^VIX':     'VIX',
    'USDJPY=X': 'USDJPY',
    'DX=F':     'DXY',
    'BTC-USD':  'BTC',
    'NTR':         'NTR',
    '017670.KS':   'SKT',
}

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
# OHLCV 데이터 Supabase 저장 + 차트 div 생성
# =============================================
def save_chart_data(client, ticker, name):
    import json
    key = CHART_KEYS.get(ticker, ticker.replace('^','').replace('=X','').replace('=',''))
    try:
        data = yf.download(ticker, period='3mo', interval='1d', progress=False, auto_adjust=True)
        if len(data) < 5:
            return
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        close = data['Close'].squeeze()
        ema20 = calc_ema(close, 20)
        ema50 = calc_ema(close, 50)
        candles = [{'time': idx.strftime('%Y-%m-%d'),
                    'open':  round(float(data.loc[idx,'Open']),4),
                    'high':  round(float(data.loc[idx,'High']),4),
                    'low':   round(float(data.loc[idx,'Low']),4),
                    'close': round(float(data.loc[idx,'Close']),4)}
                   for idx in data.index]
        ema20_list = [{'time': idx.strftime('%Y-%m-%d'), 'value': round(float(v),4)} for idx,v in ema20.items()]
        ema50_list = [{'time': idx.strftime('%Y-%m-%d'), 'value': round(float(v),4)} for idx,v in ema50.items()]
        payload = {'candles': candles, 'ema20': ema20_list, 'ema50': ema50_list}
        existing = client.table('chart_data').select('id').eq('ticker_key', key).execute()
        if existing.data:
            client.table('chart_data').update({'ohlcv': payload, 'symbol_name': name}).eq('ticker_key', key).execute()
        else:
            client.table('chart_data').insert({'ticker_key': key, 'symbol_name': name, 'ohlcv': payload}).execute()
        print(f"    차트 저장: {name}")
    except Exception as e:
        print(f"    차트 오류 ({name}): {e}")

def get_chart_div(ticker):
    key = CHART_KEYS.get(ticker, ticker.replace('^','').replace('=X','').replace('=',''))
    return f'<div class="lw-chart" data-key="{key}"></div>'

# =============================================
# 시장 등락률 (HTML)
# =============================================
def get_market_overview_html():
    items = []
    for name, ticker in MARKET_TICKERS.items():
        try:
            data = yf.download(ticker, period='2d', interval='1d', progress=False, auto_adjust=True)
            if len(data) < 2:
                continue
            close = data['Close'].squeeze()
            prev = float(close.iloc[-2])
            curr = float(close.iloc[-1])
            chg = ((curr - prev) / prev) * 100
            is_up = chg >= 0
            arrow = "▲" if is_up else "▼"
            sign = "+" if is_up else ""
            color = "#f87171" if is_up else "#60a5fa"
            items.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:9px 0;border-bottom:1px solid #1e2030;">'
                f'<span style="color:#94a3b8;font-size:13px;">{name}</span>'
                f'<div>'
                f'<span style="color:#e2e8f0;font-size:14px;font-weight:600;">{curr:,.2f}</span>'
                f'<span style="color:{color};font-size:13px;margin-left:10px;">{arrow} {sign}{chg:.2f}%</span>'
                f'</div>'
                f'</div>'
            )
        except Exception:
            pass
    return '<div style="padding:4px 0;">' + ''.join(items) + '</div>'

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

        # 종합 의견 — EMA50/200 기준 추세 맥락 반영
        e50_val  = float(emas[50].iloc[-1])  if 50  in emas else None
        e200_val = float(emas[200].iloc[-1]) if 200 in emas else None
        above_e50  = e50_val  is not None and curr_close > e50_val
        above_e200 = e200_val is not None and curr_close > e200_val
        macd_up = macd_val > sig_val

        if chg > 0 and not above_e50:
            opinion = "하락추세 속 단기 반등. 추세 전환 확인 전 신뢰도 낮음."
            op_class = "down"
        elif chg > 0 and above_e50 and not above_e200:
            opinion = "중기 반등 중이나 장기 하락추세 유지. 저항 확인 필요."
            op_class = "neutral"
        elif above_e200 and above_e50 and macd_up:
            opinion = "단기·중기 상승추세 유지. 모멘텀 지속 여부 주시."
            op_class = "up"
        elif above_e200 and not macd_up:
            opinion = "장기 추세 양호하나 단기 모멘텀 약화. 지지선 확인 필요."
            op_class = "neutral"
        elif not above_e50 and not macd_up:
            opinion = "단기·중기 하락 압력 지속. 반등 시 저항 가능성 유의."
            op_class = "down"
        else:
            opinion = "혼조 국면. 방향성 확인 후 대응 권장."
            op_class = "neutral"

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
# 특별종목 중기 모멘텀 분석 (HTML 반환)
# =============================================
def analyze_special_html(name, ticker):
    try:
        # 일봉 1년치
        data = yf.download(ticker, period='1y', interval='1d', progress=False, auto_adjust=True)
        if len(data) < 60:
            return '<p class="an-error">데이터 부족</p>'
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        close = data['Close'].squeeze()
        volume = data['Volume'].squeeze() if 'Volume' in data.columns else None
        curr = float(close.iloc[-1])

        # ── 멀티 기간 수익률 ──
        def pct(n):
            if len(close) < n + 1:
                return None
            old = float(close.iloc[-(n+1)])
            return ((curr - old) / old) * 100

        ret_5   = pct(5)
        ret_21  = pct(21)
        ret_63  = pct(63)
        ret_126 = pct(126)

        def fmt_ret(v, label):
            if v is None:
                return ''
            cls = 'up' if v >= 0 else 'down'
            sign = '+' if v >= 0 else ''
            return f'<div class="ret-item"><span class="ret-label">{label}</span><span class="ret-val {cls}">{sign}{v:.1f}%</span></div>'

        ret_html = (
            '<div class="ret-row">'
            + fmt_ret(ret_5,   '1주')
            + fmt_ret(ret_21,  '1달')
            + fmt_ret(ret_63,  '3달')
            + fmt_ret(ret_126, '6달')
            + '</div>'
        )

        # ── 52주 고저가 대비 위치 ──
        high52 = float(close.max())
        low52  = float(close.min())
        pos52  = (curr - low52) / (high52 - low52) * 100 if high52 != low52 else 50

        # ── EMA 정배열 판단 ──
        emas = {p: calc_ema(close, p) for p in [20, 50, 100, 200] if len(close) >= p}
        ema_vals = {p: float(v.iloc[-1]) for p, v in emas.items()}

        above = [p for p, v in ema_vals.items() if curr > v]
        below = [p for p, v in ema_vals.items() if curr < v]

        if len(above) == len(ema_vals):
            ema_align = '✅ 전 EMA 위 — 강한 정배열'
            ema_class = 'up'
        elif len(below) == len(ema_vals):
            ema_align = '⚠️ 전 EMA 아래 — 역배열'
            ema_class = 'down'
        else:
            ema_align = f'현재가 EMA {",".join(map(str,sorted(above)))} 위 / EMA {",".join(map(str,sorted(below)))} 아래'
            ema_class = 'neutral'

        ema_items = "".join([
            f'<span class="ema-item">EMA{p}<b>{v:,.2f}</b></span>'
            for p, v in sorted(ema_vals.items())
        ])

        # EMA 크로스 신호
        cross_signals = check_ema_cross(close) if len(close) >= 200 else []
        cross_html = (
            "".join([f'<div class="signal-badge {"dead" if "데드" in s else "golden"}">{s.strip()}</div>' for s in cross_signals])
            if cross_signals else '<span class="an-neutral">최근 크로스 없음</span>'
        )

        # ── 주봉 RSI ──
        weekly = yf.download(ticker, period='2y', interval='1wk', progress=False, auto_adjust=True)
        if isinstance(weekly.columns, pd.MultiIndex):
            weekly.columns = weekly.columns.get_level_values(0)
        wclose = weekly['Close'].squeeze() if len(weekly) >= 20 else None
        if wclose is not None and len(wclose) >= 14:
            rsi_w = float(calc_rsi(wclose).iloc[-1])
            if rsi_w >= 70:
                rsi_class, rsi_comment = 'up', '과매수 — 단기 조정 가능성'
            elif rsi_w >= 55:
                rsi_class, rsi_comment = 'up', '강세 유지 중'
            elif rsi_w >= 45:
                rsi_class, rsi_comment = 'neutral', '중립 구간'
            elif rsi_w >= 30:
                rsi_class, rsi_comment = 'down', '약세 흐름'
            else:
                rsi_class, rsi_comment = 'down', '과매도 — 반등 가능성'
            rsi_label = '주봉 RSI'
        else:
            rsi_w = float(calc_rsi(close).iloc[-1])
            rsi_class = 'up' if rsi_w >= 55 else ('down' if rsi_w <= 45 else 'neutral')
            rsi_comment = '과매수' if rsi_w >= 70 else ('과매도' if rsi_w <= 30 else '중립')
            rsi_label = 'RSI(14)'

        # ── 거래량 트렌드 (4주 vs 10주 평균) ──
        if volume is not None and len(volume) >= 50:
            vol4  = float(volume.iloc[-20:].mean())
            vol10 = float(volume.iloc[-50:].mean())
            vol_ratio = vol4 / vol10 if vol10 > 0 else 1
            if vol_ratio >= 1.3:
                vol_html = f'<span class="up">🔥 거래량 급증 (4주평균 {vol_ratio:.1f}x 10주평균)</span>'
            elif vol_ratio >= 1.1:
                vol_html = f'<span class="up">↑ 거래량 증가 중 ({vol_ratio:.1f}x)</span>'
            elif vol_ratio <= 0.7:
                vol_html = f'<span class="down">↓ 거래량 감소 중 ({vol_ratio:.1f}x)</span>'
            else:
                vol_html = f'<span class="neutral">보통 ({vol_ratio:.1f}x)</span>'
        else:
            vol_html = '<span class="neutral">N/A</span>'

        # ── SPX 대비 상대 강도 (3달) ──
        try:
            spx = yf.download('^GSPC', period='6mo', interval='1d', progress=False, auto_adjust=True)
            spx_close = spx['Close'].squeeze()
            spx_ret = ((float(spx_close.iloc[-1]) - float(spx_close.iloc[-63])) / float(spx_close.iloc[-63])) * 100
            rs_diff = (ret_63 or 0) - spx_ret
            if rs_diff > 5:
                rs_html = f'<span class="up">SPX 대비 +{rs_diff:.1f}%p 아웃퍼폼 🏆</span>'
            elif rs_diff < -5:
                rs_html = f'<span class="down">SPX 대비 {rs_diff:.1f}%p 언더퍼폼</span>'
            else:
                rs_html = f'<span class="neutral">SPX와 유사 ({rs_diff:+.1f}%p)</span>'
        except Exception:
            rs_html = '<span class="neutral">N/A</span>'

        # ── 중기 모멘텀 판단 — 조건 기반 ──
        e50_v  = ema_vals.get(50)
        e200_v = ema_vals.get(200)
        above_e50  = e50_v  is not None and curr > e50_v
        above_e200 = e200_v is not None and curr > e200_v
        ret_pos = sum(1 for r in [ret_21, ret_63, ret_126] if r is not None and r > 0)

        if above_e200 and above_e50 and ret_pos >= 2 and rsi_w >= 50:
            opinion, op_class = '중기 상승추세 유지 중. 추세 추종 유효.', 'up'
        elif above_e200 and above_e50 and ret_pos >= 1:
            opinion, op_class = '중기 추세 양호이나 모멘텀 다소 약화. 눌림 구간 주시.', 'up'
        elif above_e200 and not above_e50:
            opinion, op_class = '장기 추세는 유지되나 중기 조정 진행 중. 지지선 확인 필요.', 'neutral'
        elif not above_e200 and above_e50 and ret_pos >= 2:
            opinion, op_class = '장기 하락추세 속 중기 반등. 장기 추세 전환 확인 전 경계.', 'neutral'
        elif not above_e200 and not above_e50:
            opinion, op_class = '중기·장기 하락 압력 지속. 반등 시 저항 가능성 높음.', 'down'
        else:
            opinion, op_class = '방향성 불명확. 추세 확인 후 대응 권장.', 'neutral'

        return f'''
<div class="an-price">
  <span class="an-curr">{curr:,.2f}</span>
  <span style="font-size:11px;color:#64748b;">52주 범위 내 상위 {pos52:.0f}% 위치</span>
</div>
<div class="an-section">
  <div class="an-label">📅 기간별 수익률</div>
  {ret_html}
</div>
<div class="an-section">
  <div class="an-label">📊 EMA 구조</div>
  <div class="ema-row">{ema_items}</div>
  <div class="an-row" style="margin-top:6px"><span class="{ema_class}">{ema_align}</span></div>
  <div class="an-label" style="margin-top:8px">크로스 신호</div>
  {cross_html}
</div>
<div class="an-section">
  <div class="an-label">📈 {rsi_label}</div>
  <div class="an-row">
    <div class="rsi-bar-wrap"><div class="rsi-bar" style="width:{min(rsi_w,100):.0f}%"></div></div>
    <span class="{rsi_class}">{rsi_w:.1f} — {rsi_comment}</span>
  </div>
</div>
<div class="an-section">
  <div class="an-label">📦 거래량 트렌드</div>
  {vol_html}
</div>
<div class="an-section">
  <div class="an-label">⚖️ SPX 대비 상대강도 (3달)</div>
  {rs_html}
</div>
<div class="an-opinion {op_class}">💬 {opinion}</div>'''

    except Exception as e:
        return f'<p class="an-error">분석 오류: {e}</p>'

# =============================================
# 주식 현황 데이터 저장
# =============================================
STOCK_PRICES = {
    'KR': {
        '삼성전자':      '005930.KS',
        'SK하이닉스':    '000660.KS',
        'LG에너지솔루션':'373220.KS',
        '현대차':        '005380.KS',
        'NAVER':         '035420.KS',
        '카카오':        '035720.KS',
    },
    'US': {
        '애플':         'AAPL',
        '엔비디아':     'NVDA',
        '마이크로소프트':'MSFT',
        '테슬라':       'TSLA',
        '아마존':       'AMZN',
        '구글':         'GOOGL',
    },
    'CRYPTO': {
        '비트코인':     'BTC-USD',
        '이더리움':     'ETH-USD',
        '솔라나':       'SOL-USD',
        'XRP':          'XRP-USD',
        'BNB':          'BNB-USD',
        '도지코인':     'DOGE-USD',
        '에이다':       'ADA-USD',
        '아발란체':     'AVAX-USD',
    }
}

def update_stock_prices(client):
    rows = []
    for market, stocks in STOCK_PRICES.items():
        for name, ticker in stocks.items():
            try:
                data = yf.download(ticker, period='2d', interval='1d', progress=False, auto_adjust=True)
                if len(data) < 2:
                    continue
                close = data['Close'].squeeze()
                prev = float(close.iloc[-2])
                curr = float(close.iloc[-1])
                chg = ((curr - prev) / prev) * 100
                sign = "+" if chg >= 0 else ""
                is_up = chg >= 0
                if market == 'KR':
                    price_str = f"{curr:,.0f}원"
                    chg_str = f"{sign}{curr - prev:,.0f}"
                elif market == 'CRYPTO':
                    price_str = f"${curr:,.4f}" if curr < 1 else f"${curr:,.2f}"
                    chg_str = f"{sign}${abs(curr - prev):,.4f}" if curr < 1 else f"{sign}${abs(curr - prev):,.2f}"
                else:
                    price_str = f"${curr:,.2f}"
                    chg_str = f"{sign}${abs(curr - prev):,.2f}"
                rows.append({
                    'market': market,
                    'name': name,
                    'ticker': ticker.replace('.KS','').replace('-USD',''),
                    'price': price_str,
                    'change_val': chg_str,
                    'change_pct': f"{sign}{chg:.2f}%",
                    'is_up': is_up,
                })
                print(f"    {name}: {price_str} ({sign}{chg:.2f}%)")
            except Exception as e:
                print(f"    {name} 오류: {e}")

    if rows:
        client.table('stock_prices').delete().neq('id', 0).execute()
        client.table('stock_prices').insert(rows).execute()
        print(f"  주식 현황 {len(rows)}개 저장 완료")

# =============================================
# 특별 분석 종목 저장
# =============================================
def save_special_ticker(client, name, ticker):
    try:
        existing = client.table('special_tickers').select('id').eq('ticker', ticker).execute()
        if not existing.data:
            client.table('special_tickers').insert({
                'name': name,
                'ticker': ticker,
                'first_date': datetime.now().strftime('%Y-%m-%d'),
            }).execute()
            print(f"  특별종목 저장: {name} ({ticker})")
    except Exception as e:
        print(f"  특별종목 저장 오류: {e}")

# =============================================
# Supabase 게시글 업로드
# =============================================
def post_to_supabase(client, title, content):
    client.table('posts').insert({
        'category': '📊 장중 브리핑',
        'title': title,
        'content': content,
        'views': 0
    }).execute()

# =============================================
# 메인
# =============================================
def main():
    now = datetime.now()
    if now.weekday() >= 5:  # 5=토, 6=일
        print(f"[{now.strftime('%H:%M:%S')}] 주말({['월','화','수','목','금','토','일'][now.weekday()]})이므로 브리핑을 건너뜁니다.")
        return
    today = now.strftime('%Y년 %m월 %d일')
    print(f"[{now.strftime('%H:%M:%S')}] 브리핑 생성 시작...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  주식 현황 업데이트 중...")
    update_stock_prices(client)

    print("  시장 데이터 수집 중...")
    market_html = get_market_overview_html()

    print("  차트 데이터 저장 중...")
    for name, ticker in MARKET_TICKERS.items():
        save_chart_data(client, ticker, name)
    for name, ticker in ANALYSIS_TICKERS.items():
        save_chart_data(client, ticker, name)

    print("  분석 생성 중...")
    market_sections = ""
    for name, ticker in MARKET_TICKERS.items():
        print(f"    {name} 분석 중...")
        chart_div = get_chart_div(ticker)
        analysis_html = analyze_ticker_html(name, ticker)
        market_sections += f'''
<div class="ticker-section">
  <h3 class="ticker-title">{name}</h3>
  {chart_div}
  <div class="analysis-box">
    {analysis_html}
  </div>
</div>'''

    special_sections = ""
    for name, ticker in ANALYSIS_TICKERS.items():
        print(f"    {name} 특별분석 중...")
        save_special_ticker(client, name, ticker)
        chart_div = get_chart_div(ticker)
        analysis_html = analyze_special_html(name, ticker)
        report_text = read_report(ticker)
        report_html = ''
        if report_text:
            print(f"    {ticker}.docx 보고서 발견, 추가 중...")
            report_html = f'''
<div style="margin-top:16px;padding:16px;background:#0e1117;border-radius:10px;border:1px solid #2d3748;">
  <div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:12px;">📄 리서치 보고서</div>
  {report_to_html(report_text)}
</div>'''
        special_sections += f'''
<div class="ticker-section special">
  <h3 class="ticker-title">⭐ {name} — 중기 모멘텀 분석</h3>
  {chart_div}
  <div class="analysis-box">
    {analysis_html}
    {report_html}
  </div>
</div>'''

    title = f"{today} 장중 브리핑"
    content = (
        '<div class="briefing">'
        '<h3>🌍 주요 시장 현황</h3>'
        f'{market_html}'
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
