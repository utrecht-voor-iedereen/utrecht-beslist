/**
 * Client-side interaction, search, dark mode, keyboard shortcuts, TTS audio & sharing for Utrecht Beslist
 */

const UTRECHT_POSTAL_MAP = {
  "3511": "Binnenstad", "3512": "Binnenstad", "3513": "Binnenstad", "3514": "Noordoost",
  "3515": "Noordoost", "3521": "Zuid", "3522": "Zuid", "3523": "Zuid", "3524": "Zuid",
  "3525": "Zuid", "3526": "Zuidwest", "3527": "Zuidwest", "3531": "West", "3532": "West",
  "3533": "West", "3534": "West", "3541": "Leidsche Rijn", "3542": "Leidsche Rijn",
  "3543": "Leidsche Rijn", "3544": "Leidsche Rijn", "3545": "Vleuten-De Meern",
  "3551": "Noordwest", "3552": "Noordwest", "3553": "Noordwest", "3554": "Noordwest",
  "3555": "Noordwest", "3561": "Overvecht", "3562": "Overvecht", "3563": "Overvecht",
  "3564": "Overvecht", "3565": "Overvecht", "3566": "Overvecht", "3571": "Noordoost",
  "3572": "Noordoost", "3573": "Noordoost", "3581": "Oost", "3582": "Oost",
  "3583": "Oost", "3584": "Oost", "3585": "Oost"
};

const HUMAN_IMPACT_THEMES = {
  "casa": ["wonen", "groen-klimaat", "jeugd-onderwijs"],
  "bolsillo": ["bestuur-financien", "zorg"],
  "movilidad": ["verkeer", "veiligheid", "cultuur-evenementen"]
};

// Dark Mode Initialization
(function initTheme() {
  const savedTheme = localStorage.getItem('utrecht_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
})();

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const filterChips = document.querySelectorAll('.filter-chip');
  const humanImpactBtns = document.querySelectorAll('.human-impact-btn');
  const cardsGrid = document.getElementById('cards-grid');
  const cards = document.querySelectorAll('.card');
  const langBtns = document.querySelectorAll('.lang-btn');
  const postalBadge = document.getElementById('postal-badge');
  const mapPaths = document.querySelectorAll('.wijk-map-path');
  const viewToggleBtns = document.querySelectorAll('.view-toggle-btn');
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const resultsCounterBadge = document.getElementById('results-counter-badge');

  let activeTheme = 'all';
  let activeHumanImpactGroup = 'all';
  let activeWijk = 'all';
  let searchQuery = '';
  let detectedWijk = '';

  // Dark Mode Toggle
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('utrecht_theme', newTheme);
      themeToggleBtn.textContent = newTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
    });
    
    const initialTheme = localStorage.getItem('utrecht_theme') || 'light';
    themeToggleBtn.textContent = initialTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
  }

  // Language Switcher Logic
  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetLang = btn.dataset.lang;
      const currentPath = window.location.pathname;
      
      if (targetLang === 'en') {
        if (currentPath.includes('/nl/besluit/')) {
          window.location.href = currentPath.replace('/nl/besluit/', '/en/decision/');
        } else if (currentPath.includes('/nl/')) {
          window.location.href = currentPath.replace('/nl/', '/en/');
        }
      } else if (targetLang === 'nl') {
        if (currentPath.includes('/en/decision/')) {
          window.location.href = currentPath.replace('/en/decision/', '/nl/besluit/');
        } else if (currentPath.includes('/en/')) {
          window.location.href = currentPath.replace('/en/', '/nl/');
        }
      }
    });
  });

  // Postal Code Lookup
  function checkPostalCode(query) {
    const match = query.match(/\b(35\d{2})\b/);
    if (match && UTRECHT_POSTAL_MAP[match[1]]) {
      detectedWijk = UTRECHT_POSTAL_MAP[match[1]];
      if (postalBadge) {
        postalBadge.style.display = 'inline-block';
        postalBadge.textContent = `📍 Postcode ${match[1]} → Wijk ${detectedWijk}`;
      }
    } else {
      detectedWijk = '';
      if (postalBadge) {
        postalBadge.style.display = 'none';
      }
    }
  }

  // Filter Cards Logic
  function filterCards() {
    let visibleCount = 0;
    cards.forEach(card => {
      const cardTheme = card.dataset.theme || '';
      const cardWijk = card.dataset.wijk || '';
      const titleText = card.querySelector('.card-title')?.textContent.toLowerCase() || '';
      const summaryText = card.querySelector('.card-summary')?.textContent.toLowerCase() || '';
      const tagsText = Array.from(card.querySelectorAll('.tag')).map(t => t.textContent.toLowerCase()).join(' ');

      // Theme Filter
      const matchesTheme = (activeTheme === 'all' || cardTheme.includes(activeTheme) || tagsText.includes(activeTheme));
      
      // Human Impact Group Filter
      let matchesHumanImpact = true;
      if (activeHumanImpactGroup !== 'all') {
        const allowedThemes = HUMAN_IMPACT_THEMES[activeHumanImpactGroup] || [];
        matchesHumanImpact = allowedThemes.some(th => cardTheme.includes(th));
      }

      // Wijk Filter
      const targetWijk = activeWijk !== 'all' ? activeWijk.toLowerCase() : (detectedWijk ? detectedWijk.toLowerCase() : '');
      const matchesWijk = !targetWijk || cardWijk.includes(targetWijk) || tagsText.includes(targetWijk);

      // Search Query Filter
      const matchesSearch = !searchQuery || titleText.includes(searchQuery) || summaryText.includes(searchQuery) || tagsText.includes(searchQuery);

      if (matchesTheme && matchesHumanImpact && matchesWijk && matchesSearch) {
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

    if (resultsCounterBadge) {
      resultsCounterBadge.textContent = `${visibleCount} ${visibleCount === 1 ? 'item' : 'items'}`;
    }
  }

  // Search Input Event
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      checkPostalCode(searchQuery);
      filterCards();
    });
  }

  // Human Impact Group Buttons Event
  humanImpactBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      humanImpactBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeHumanImpactGroup = btn.dataset.impactGroup || 'all';
      filterCards();
    });
  });

  // Specific Theme Filter Chips Event
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeTheme = chip.dataset.theme || 'all';
      filterCards();
    });
  });

  // Neighborhood Filter Clicks
  mapPaths.forEach(path => {
    path.addEventListener('click', () => {
      mapPaths.forEach(p => p.classList.remove('active', 'selected'));
      path.classList.add('active', 'selected');
      activeWijk = path.dataset.wijk || 'all';
      filterCards();
    });
  });

  // View Mode Switcher Event
  viewToggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      viewToggleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const viewMode = btn.dataset.viewMode;
      if (cardsGrid) {
        if (viewMode === 'list') {
          cardsGrid.classList.add('view-list-mode');
        } else {
          cardsGrid.classList.remove('view-list-mode');
        }
      }
    });
  });

  // Keyboard Shortcuts (UI-UX Pro Max)
  document.addEventListener('keydown', (e) => {
    // Focus Search with '/' or 'Ctrl+K' / 'Cmd+K'
    if (e.key === '/' || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
      if (searchInput && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    }
    
    // Clear Filters with 'Esc'
    if (e.key === 'Escape') {
      if (searchInput) searchInput.value = '';
      searchQuery = '';
      activeTheme = 'all';
      activeHumanImpactGroup = 'all';
      activeWijk = 'all';
      detectedWijk = '';
      
      filterChips.forEach(c => c.classList.remove('active'));
      document.querySelector('.filter-chip[data-theme="all"]')?.classList.add('active');

      humanImpactBtns.forEach(b => b.classList.remove('active'));
      document.querySelector('.human-impact-btn[data-impact-group="all"]')?.classList.add('active');

      mapPaths.forEach(p => p.classList.remove('active', 'selected'));
      document.querySelector('.wijk-map-path[data-wijk="all"]')?.classList.add('active');

      if (postalBadge) postalBadge.style.display = 'none';

      filterCards();
    }

    // Toggle View Mode with 'L' key (when not typing in search)
    if (e.key.toLowerCase() === 'l' && document.activeElement !== searchInput) {
      const activeBtn = document.querySelector('.view-toggle-btn.active');
      const isCards = activeBtn?.dataset.viewMode === 'cards';
      const targetBtn = document.querySelector(`.view-toggle-btn[data-view-mode="${isCards ? 'list' : 'cards'}"]`);
      targetBtn?.click();
    }
  });

  // Initial filter run to populate badge count
  filterCards();
});

// Share Function
function shareCard(title, url) {
  if (navigator.share) {
    navigator.share({
      title: title,
      text: `Utrecht Beslist: ${title}`,
      url: url || window.location.href
    }).catch(() => {});
  } else {
    navigator.clipboard.writeText(`${title} - ${url || window.location.href}`);
    alert('Link gekopieerd naar klembord! / Link copied to clipboard!');
  }
}

// Text-to-Speech (TTS Audio Read-Aloud) Function (UI-UX Pro Max)
function speakText(text, lang = 'nl-NL') {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel(); // Stop ongoing speech
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'en' ? 'en-US' : 'nl-NL';
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  } else {
    alert('Audio read-aloud is not supported on this browser.');
  }
}
