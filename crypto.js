function createCryptoCard(s) {
  return '<div class="stock-card">' +
    '<div class="stock-name">' + s.name + ' <span class="stock-ticker">' + s.ticker + '</span></div>' +
    '<div class="stock-price">' + s.price + '</div>' +
    '<div class="stock-change ' + (s.is_up ? 'up' : 'down') + '">' + s.change_val + ' (' + s.change_pct + ')</div>' +
    '</div>';
}

async function loadCrypto() {
  var gridEl = document.getElementById('cryptoGrid');
  var updatedEl = document.getElementById('cryptoUpdated');

  try {
    var res = await db.from('stock_prices').select('*').eq('market', 'CRYPTO').order('id');
    if (res.error) throw res.error;
    var data = res.data || [];

    if (!data.length) {
      gridEl.innerHTML = '<p style="color:#64748b;padding:16px">데이터 없음 (자동 업데이트 대기 중)</p>';
      updatedEl.textContent = '매일 오전 3시 자동 갱신';
      return;
    }

    gridEl.innerHTML = data.map(createCryptoCard).join('');
    var updated = new Date(data[0].updated_at);
    updatedEl.textContent = '최근 업데이트: ' + updated.toLocaleString('ko-KR');
  } catch(err) {
    updatedEl.textContent = '오류: ' + err.message;
    console.error(err);
  }
}

loadCrypto();
