// ── 히트맵 이미지 강제 새로고침 ───────────────────────────────────────────────
function forceReloadImages() {
  var t = Date.now();
  document.querySelectorAll('.finviz-map-img').forEach(function(img) {
    var base = img.src.split('?')[0];
    img.src = base + '?t=' + t;
  });
}

// ── 갱신 버튼 상태 제어 ───────────────────────────────────────────────────────
function setRefreshBtn(state, msg) {
  var btn    = document.getElementById('refreshBtn');
  var txt    = document.getElementById('refreshBtnText');
  var status = document.getElementById('refreshStatus');
  if (state === 'ready')   { btn.disabled = false; btn.classList.remove('used','loading'); txt.textContent = '🔄 히트맵 갱신'; }
  if (state === 'loading') { btn.disabled = true;  btn.classList.add('loading');           txt.textContent = '⏳ 갱신 중...'; }
  if (state === 'used')    { btn.disabled = true;  btn.classList.remove('loading'); btn.classList.add('used'); txt.textContent = '✅ 갱신 완료'; }
  if (state === 'error')   { btn.disabled = true;  btn.classList.remove('loading'); btn.classList.add('used'); txt.textContent = '⚠️ 갱신 오류'; }
  if (status) status.textContent = msg || '';
}

// ── 하루 1회 제한 ─────────────────────────────────────────────────────────────
function getToday7am() {
  var d = new Date();
  d.setHours(7, 0, 0, 0);
  return d;
}
function canPressRefresh() {
  var stored = localStorage.getItem('stockRefresh');
  if (!stored) return true;
  return new Date(JSON.parse(stored).pressedAt) < getToday7am();
}
function markRefreshUsed() {
  localStorage.setItem('stockRefresh', JSON.stringify({ pressedAt: new Date().toISOString() }));
}

// ── 갱신 버튼 클릭 핸들러 ────────────────────────────────────────────────────
async function handleRefresh() {
  if (!canPressRefresh()) return;
  if (!db) { setRefreshBtn('error', 'DB 연결 없음'); return; }

  markRefreshUsed();
  setRefreshBtn('loading', '요청 전송 중...');

  try {
    var ins = await db.from('refresh_trigger').insert({ status: 'pending' }).select().single();
    if (ins.error) throw ins.error;
    var triggerId = ins.data.id;
    setRefreshBtn('loading', '이미지 생성 중... (최대 3분 소요)');

    var attempts = 0;
    var poll = setInterval(async function() {
      attempts++;
      try {
        var res = await db.from('refresh_trigger').select('status').eq('id', triggerId).single();
        if (res.data) {
          if (res.data.status === 'done') {
            clearInterval(poll);
            forceReloadImages();
            setRefreshBtn('used', '히트맵이 업데이트됐습니다.');
          } else if (res.data.status === 'error') {
            clearInterval(poll);
            setRefreshBtn('error', '갱신 중 오류가 발생했습니다.');
          }
        }
      } catch(e) {}
      if (attempts >= 36) {
        clearInterval(poll);
        setRefreshBtn('error', '응답 시간 초과. 잠시 후 새로고침 해보세요.');
      }
    }, 5000);

  } catch(e) {
    setRefreshBtn('error', '요청 실패: ' + e.message);
  }
}

// ── 페이지 로드 시 버튼 초기 상태 설정 ───────────────────────────────────────
(function() {
  if (!canPressRefresh()) {
    setRefreshBtn('used', '오늘 갱신 완료. 내일 오전 7시 초기화.');
  }
})();
