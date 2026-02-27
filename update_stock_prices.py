#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_stock_prices.py - stock_prices 테이블 현재가 일괄 업데이트"""

import yfinance as yf
from datetime import datetime, timezone
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
    'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6'
    'InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.'
    'rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'
)

# (market, 표시이름, DB ticker, yfinance ticker)
STOCKS = [
    ('KR',     '삼성전자',       '005930', '005930.KS'),
    ('KR',     'SK하이닉스',     '000660', '000660.KS'),
    ('KR',     'NAVER',          '035420', '035420.KS'),
    ('KR',     '카카오',         '035720', '035720.KS'),
    ('KR',     '현대차',         '005380', '005380.KS'),
    ('KR',     'LG에너지솔루션', '373220', '373220.KS'),
    ('US',     '애플',           'AAPL',   'AAPL'),
    ('US',     '마이크로소프트', 'MSFT',   'MSFT'),
    ('US',     '구글',           'GOOGL',  'GOOGL'),
    ('US',     '엔비디아',       'NVDA',   'NVDA'),
    ('CRYPTO', '비트코인',       'BTC',    'BTC-USD'),
    ('CRYPTO', '이더리움',       'ETH',    'ETH-USD'),
    ('CRYPTO', '솔라나',         'SOL',    'SOL-USD'),
    ('CRYPTO', 'BNB',            'BNB',    'BNB-USD'),
    ('CRYPTO', 'XRP',            'XRP',    'XRP-USD'),
    ('CRYPTO', '에이다',         'ADA',    'ADA-USD'),
    ('CRYPTO', '도지코인',       'DOGE',   'DOGE-USD'),
    ('CRYPTO', '아발란체',       'AVAX',   'AVAX-USD'),
]


def fmt_price(price, market):
    if market == 'KR':
        return f"{price:,.0f}원"
    elif market == 'US':
        return f"${price:,.2f}"
    else:  # CRYPTO
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        else:
            return f"${price:.6f}"


def fmt_change(chg, market):
    """change_val 포맷 - KR은 +/-부호 포함, US/CRYPTO는 절대값 $ 표시"""
    if market == 'KR':
        sign = '+' if chg >= 0 else '-'
        return f"{sign}{abs(chg):,.0f}"
    elif market == 'US':
        return f"${abs(chg):,.2f}"
    else:  # CRYPTO
        if abs(chg) >= 1:
            return f"${abs(chg):,.2f}"
        elif abs(chg) >= 0.0001:
            return f"${abs(chg):.4f}"
        else:
            return f"${abs(chg):.6f}"


def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    now = datetime.now(timezone.utc).isoformat()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] stock_prices 업데이트 시작\n")

    for market, name, db_ticker, yf_ticker in STOCKS:
        try:
            data = yf.download(yf_ticker, period='5d', interval='1d',
                               progress=False, auto_adjust=True)
            if len(data) < 2:
                print(f"  [{market}] {name}: 데이터 부족 ({len(data)}행)")
                continue

            close = data['Close'].squeeze()
            prev  = float(close.iloc[-2])
            curr  = float(close.iloc[-1])
            chg   = curr - prev
            chg_pct = (chg / prev) * 100
            is_up = chg >= 0
            sign  = '+' if is_up else ''

            row = {
                'market':     market,
                'name':       name,
                'ticker':     db_ticker,
                'price':      fmt_price(curr, market),
                'change_val': fmt_change(chg, market),
                'change_pct': f"{sign}{chg_pct:.2f}%",
                'is_up':      is_up,
                'updated_at': now,
            }

            existing = (client.table('stock_prices')
                        .select('id').eq('ticker', db_ticker).execute())
            if existing.data:
                client.table('stock_prices').update(row).eq('ticker', db_ticker).execute()
            else:
                client.table('stock_prices').insert(row).execute()

            arrow = '▲' if is_up else '▼'
            print(f"  [{market}] {name}: {fmt_price(curr, market)}  "
                  f"{arrow} {sign}{chg_pct:.2f}%")

        except Exception as e:
            print(f"  [{market}] {name} 오류: {e}")

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 완료!")


if __name__ == '__main__':
    main()
