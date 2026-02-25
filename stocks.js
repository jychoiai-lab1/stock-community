function createStockCard(s) {
  return '<div class="stock-card">' +
    '<div class="stock-name">' + s.name + ' <span class="stock-ticker">' + s.ticker + '</span></div>' +
    '<div class="stock-price">' + s.price + '</div>' +
    '<div class="stock-change ' + (s.is_up ? 'up' : 'down') + '">' + s.change_val + ' (' + s.change_pct + ')</div>' +
    '</div>';
}

async function loadStocks() {
  var krEl = document.getElementById('krStocks');
  var usEl = document.getElementById('usStocks');
  var updatedEl = document.getElementById('stocksUpdated');

  try {
    if (db) {
      var res = await db.from('stock_prices').select('*').order('id');
      if (res.error) throw res.error;
      var data = res.data || [];

      var kr = data.filter(function(s){ return s.market === 'KR'; });
      var us = data.filter(function(s){ return s.market === 'US'; });

      krEl.innerHTML = kr.length ? kr.map(createStockCard).join('') : '<p style="color:#64748b;padding:16px">데이터 없음</p>';
      usEl.innerHTML = us.length ? us.map(createStockCard).join('') : '<p style="color:#64748b;padding:16px">데이터 없음</p>';

      if (data.length > 0) {
        var updated = new Date(data[0].updated_at);
        updatedEl.textContent = '최근 업데이트: ' + updated.toLocaleString('ko-KR');
      }
    } else {
      updatedEl.textContent = 'Supabase 연결 필요';
      krEl.innerHTML = '<p style="color:#64748b;padding:16px">연결 대기 중...</p>';
      usEl.innerHTML = '<p style="color:#64748b;padding:16px">연결 대기 중...</p>';
    }
  } catch(err) {
    updatedEl.textContent = '오류: ' + err.message;
    console.error(err);
  }
}

loadStocks();
