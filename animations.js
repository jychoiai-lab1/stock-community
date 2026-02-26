// Apple-like scroll fade-in animations

const CARD_SELECTORS = '.post-card, .stock-card, .board-card, .market-block, .ticker-section, .sidebar-ticker';

const io = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      io.unobserve(entry.target);
    }
  });
}, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

function applyFadeIn(container) {
  const cards = container.querySelectorAll(CARD_SELECTORS);
  cards.forEach((card, i) => {
    if (card.dataset.animated) return;
    card.dataset.animated = '1';
    card.classList.add('fade-in');
    card.style.transitionDelay = `${i * 0.07}s`;
    io.observe(card);
  });
}

// MutationObserver: innerHTML 변경 감지
const mo = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    // innerHTML 교체 시 부모 노드 기준으로 다시 스캔
    if (mutation.addedNodes.length > 0) {
      applyFadeIn(mutation.target);
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1) applyFadeIn(node);
      });
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
  mo.observe(document.body, { childList: true, subtree: true });
  // 이미 렌더된 요소 처리
  applyFadeIn(document.body);
});

// 혹시 DOMContentLoaded 이후에 로드되는 경우 대비
window.addEventListener('load', () => {
  applyFadeIn(document.body);
});
