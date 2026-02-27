// ── 토스트 알림 ───────────────────────────────────────────────────────────────
function showToast(msg, type) {
  type = type || 'info';
  var existing = document.querySelectorAll('.toast');
  existing.forEach(function(t) { t.remove(); });

  var toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.textContent = msg;
  document.body.appendChild(toast);

  requestAnimationFrame(function() {
    toast.classList.add('toast-show');
  });
  setTimeout(function() {
    toast.classList.remove('toast-show');
    setTimeout(function() { toast.remove(); }, 350);
  }, 3000);
}

// ── 맨 위로 버튼 ─────────────────────────────────────────────────────────────
(function() {
  var btn = document.createElement('button');
  btn.id = 'backToTop';
  btn.className = 'back-to-top';
  btn.innerHTML = '↑';
  btn.title = '맨 위로';
  btn.onclick = function() { window.scrollTo({ top: 0, behavior: 'smooth' }); };
  document.body.appendChild(btn);

  window.addEventListener('scroll', function() {
    btn.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });
})();
