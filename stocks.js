var stockData = {
  kr: [
    { name: '삼성전자', ticker: '005930', price: '72,000원', change: '+800', pct: '+1.12%', up: true },
    { name: 'SK하이닉스', ticker: '000660', price: '148,000원', change: '+2,200', pct: '+1.51%', up: true },
    { name: 'LG에너지솔루션', ticker: '373220', price: '385,000원', change: '-5,000', pct: '-1.28%', up: false },
    { name: '현대차', ticker: '005380', price: '215,000원', change: '+3,000', pct: '+1.41%', up: true },
    { name: 'NAVER', ticker: '035420', price: '178,500원', change: '+1,500', pct: '+0.85%', up: true },
    { name: '카카오', ticker: '035720', price: '52,300원', change: '-200', pct: '-0.38%', up: false }
  ],
  us: [
    { name: '애플', ticker: 'AAPL', price: '$215.30', change: '+$1.70', pct: '+0.80%', up: true },
    { name: '엔비디아', ticker: 'NVDA', price: '$875.20', change: '+$18.10', pct: '+2.11%', up: true },
    { name: '마이크로소프트', ticker: 'MSFT', price: '$415.80', change: '+$3.20', pct: '+0.78%', up: true },
    { name: '테슬라', ticker: 'TSLA', price: '$280.50', change: '-$1.40', pct: '-0.50%', up: false },
    { name: '아마존', ticker: 'AMZN', price: '$196.40', change: '+$2.10', pct: '+1.08%', up: true },
    { name: '구글', ticker: 'GOOGL', price: '$172.30', change: '+$0.90', pct: '+0.52%', up: true }
  ]
};
function createStockCard(s) {
  return '<div class="stock-card"><div class="stock-name">' + s.name + ' <span class="stock-ticker">' + s.ticker + '</span></div><div class="stock-price">' + s.price + '</div><div class="stock-change ' + (s.up ? 'up' : 'down') + '">' + s.change + ' (' + s.pct + ')</div></div>';
}
setTimeout(function() {
  document.getElementById('krStocks').innerHTML = stockData.kr.map(createStockCard).join('');
  document.getElementById('usStocks').innerHTML = stockData.us.map(createStockCard).join('');
  document.getElementById('stocksUpdated').textContent = '최근 업데이트: 2026.02.25 08:00 (자동화 설정 후 실시간 반영)';
}, 500);
