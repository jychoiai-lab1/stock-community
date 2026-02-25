var boardPosts = [];

function formatDate(d) {
  var dt = new Date(d), now = new Date(), diff = Math.floor((now - dt) / 60000);
  if (diff < 1) return '방금 전';
  if (diff < 60) return diff + '분 전';
  if (diff < 1440) return Math.floor(diff / 60) + '시간 전';
  return dt.getFullYear() + '.' + String(dt.getMonth()+1).padStart(2,'0') + '.' + String(dt.getDate()).padStart(2,'0');
}

async function loadBoard() {
  var list = document.getElementById('boardList');
  try {
    var res = await db.from('board_posts').select('*').order('created_at', { ascending: false });
    if (res.error) throw res.error;
    boardPosts = res.data || [];
    if (!boardPosts.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💬</div><div class="empty-state-text">첫 번째 글을 남겨보세요!</div></div>';
      return;
    }
    list.innerHTML = boardPosts.map(function(p) {
      return '<div class="board-card" id="bcard-' + p.id + '">' +
        '<div class="board-card-header">' +
          '<span class="board-nickname">' + escapeHtml(p.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(p.created_at) + '</span>' +
        '</div>' +
        '<div class="board-card-content">' + escapeHtml(p.content) + '</div>' +
        '<div class="board-card-footer">' +
          '<button class="board-like" onclick="likePost(' + p.id + ')">❤️ ' + (p.likes || 0) + '</button>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">오류: ' + e.message + '</div></div>';
  }
}

async function submitPost() {
  var nickname = document.getElementById('nickname').value.trim();
  var content = document.getElementById('boardContent').value.trim();
  if (!nickname) { alert('닉네임을 입력해주세요'); return; }
  if (!content) { alert('내용을 입력해주세요'); return; }
  var btn = document.querySelector('.board-submit');
  btn.disabled = true;
  btn.textContent = '등록 중...';
  try {
    var res = await db.from('board_posts').insert({ nickname: nickname, content: content, likes: 0 });
    if (res.error) throw res.error;
    document.getElementById('boardContent').value = '';
    document.getElementById('charCount').textContent = '0 / 300';
    await loadBoard();
  } catch(e) {
    alert('오류: ' + e.message);
  }
  btn.disabled = false;
  btn.textContent = '등록';
}

async function likePost(id) {
  var post = boardPosts.find(function(p) { return p.id === id; });
  if (!post) return;
  var newLikes = (post.likes || 0) + 1;
  post.likes = newLikes;
  var btn = document.querySelector('#bcard-' + id + ' .board-like');
  if (btn) btn.textContent = '❤️ ' + newLikes;
  await db.from('board_posts').update({ likes: newLikes }).eq('id', id);
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

document.getElementById('boardContent').addEventListener('input', function() {
  document.getElementById('charCount').textContent = this.value.length + ' / 300';
});

loadBoard();
