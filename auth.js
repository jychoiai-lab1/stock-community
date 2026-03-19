(function() {
  if (sessionStorage.getItem('auth') === 'ok') return;

  // 오버레이 생성
  var overlay = document.createElement('div');
  overlay.id = 'authOverlay';
  overlay.innerHTML =
    '<div class="auth-box">' +
      '<div class="auth-logo">📈 겁쟁이리서치</div>' +
      '<div class="auth-desc">비밀번호를 입력해주세요</div>' +
      '<input type="password" id="authInput" class="auth-input" placeholder="비밀번호" maxlength="20" />' +
      '<div class="auth-error" id="authError"></div>' +
      '<button class="auth-btn" onclick="checkAuth()">입장</button>' +
    '</div>';

  var style = document.createElement('style');
  style.textContent =
    '#authOverlay{position:fixed;inset:0;background:#0e1117;z-index:9999;display:flex;align-items:center;justify-content:center;}' +
    '.auth-box{background:#161b27;border:1px solid #2d3748;border-radius:20px;padding:36px 32px;width:100%;max-width:340px;text-align:center;}' +
    '.auth-logo{font-size:20px;font-weight:700;color:#60a5fa;margin-bottom:8px;}' +
    '.auth-desc{font-size:14px;color:#64748b;margin-bottom:24px;}' +
    '.auth-input{width:100%;background:#0e1117;border:1px solid #2d3748;border-radius:10px;padding:12px 16px;color:#e2e8f0;font-size:16px;text-align:center;letter-spacing:4px;outline:none;box-sizing:border-box;}' +
    '.auth-input:focus{border-color:#60a5fa;}' +
    '.auth-error{font-size:13px;color:#f87171;margin-top:8px;height:18px;}' +
    '.auth-btn{margin-top:16px;width:100%;background:#1e3a5f;color:#60a5fa;border:1px solid #1d4ed8;border-radius:10px;padding:12px;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.15s;}' +
    '.auth-btn:hover{background:#1d4ed8;color:#fff;}';

  document.head.appendChild(style);
  document.body.appendChild(overlay);

  // 엔터키 지원
  document.getElementById('authInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') checkAuth();
  });
  document.getElementById('authInput').focus();
})();

function checkAuth() {
  var input = document.getElementById('authInput').value;
  if (input === '1018') {
    sessionStorage.setItem('auth', 'ok');
    document.getElementById('authOverlay').remove();
  } else {
    document.getElementById('authError').textContent = '비밀번호가 틀렸습니다';
    document.getElementById('authInput').value = '';
    document.getElementById('authInput').focus();
  }
}
