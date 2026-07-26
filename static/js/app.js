/**
 * Client-side interaction & filtering for Utrecht Beslist
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const filterChips = document.querySelectorAll('.filter-chip');
  const cards = document.querySelectorAll('.card');
  const langBtns = document.querySelectorAll('.lang-btn');

  let activeTheme = 'all';
  let searchQuery = '';

  // Language Switcher Logic
  langBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetLang = btn.dataset.lang;
      const currentPath = window.location.pathname;
      if (targetLang === 'en' && !currentPath.includes('/en/')) {
        window.location.href = '../en/index.html';
      } else if (targetLang === 'nl' && !currentPath.includes('/nl/')) {
        window.location.href = '../nl/index.html';
      }
    });
  });

  // Filter Cards Logic
  function filterCards() {
    let visibleCount = 0;
    cards.forEach(card => {
      const cardTheme = card.dataset.theme || '';
      const titleText = card.querySelector('.card-title')?.textContent.toLowerCase() || '';
      const summaryText = card.querySelector('.card-summary')?.textContent.toLowerCase() || '';
      const tagsText = Array.from(card.querySelectorAll('.tag')).map(t => t.textContent.toLowerCase()).join(' ');

      const matchesTheme = (activeTheme === 'all' || cardTheme.includes(activeTheme) || tagsText.includes(activeTheme));
      const matchesSearch = !searchQuery || titleText.includes(searchQuery) || summaryText.includes(searchQuery) || tagsText.includes(searchQuery);

      if (matchesTheme && matchesSearch) {
        card.style.display = 'flex';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    const noResultsEl = document.getElementById('no-results');
    if (noResultsEl) {
      noResultsEl.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  // Search Input Event
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      filterCards();
    });
  }

  // Filter Chips Event
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeTheme = chip.dataset.theme || 'all';
      filterCards();
    });
  });
});
