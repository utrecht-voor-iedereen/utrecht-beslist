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

// Contact address for error / suggestion reports (change this before deploying)
const REPORT_EMAIL = "ipereferr@gmail.com";
const REPORT_COOLDOWN_MS = 60000; // 1 minute client-side cooldown between reports
const REPORT_COOLDOWN_KEY = 'utrecht_report_last_sent';

// Dark Mode Initialization
(function initTheme() {
  const savedTheme = localStorage.getItem('utrecht_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
})();

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const humanImpactBtns = document.querySelectorAll('.human-impact-btn');
  const wijkSelect = document.getElementById('wijk-select');
  const themeSelect = document.getElementById('theme-select');
  const cardsGrid = document.getElementById('cards-grid');
  const cards = document.querySelectorAll('.card');
  const langBtns = document.querySelectorAll('.lang-btn');
  const postalBadge = document.getElementById('postal-badge');
  const viewToggleBtns = document.querySelectorAll('.view-toggle-btn');
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const resultsCounterBadge = document.getElementById('results-counter-badge');
  const resetFiltersBtn = document.getElementById('reset-filters-btn');

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

  // Reset Filters Function
  function resetAllFilters() {
    if (searchInput) searchInput.value = '';
    searchQuery = '';
    activeTheme = 'all';
    activeHumanImpactGroup = 'all';
    activeWijk = 'all';
    detectedWijk = '';
    
    if (wijkSelect) wijkSelect.value = 'all';
    if (themeSelect) themeSelect.value = 'all';

    humanImpactBtns.forEach(b => b.classList.remove('active'));
    document.querySelector('.human-impact-btn[data-impact-group="all"]')?.classList.add('active');

    if (postalBadge) postalBadge.style.display = 'none';

    filterCards();
  }

  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', resetAllFilters);
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

    // Toggle Reset Button
    const isFiltered = (activeTheme !== 'all' || activeHumanImpactGroup !== 'all' || activeWijk !== 'all' || searchQuery !== '');
    if (resetFiltersBtn) {
      resetFiltersBtn.style.display = isFiltered ? 'inline-flex' : 'none';
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

  // Wijk Select Event (Option A)
  if (wijkSelect) {
    wijkSelect.addEventListener('change', (e) => {
      activeWijk = e.target.value;
      filterCards();
    });
  }

  // Theme Select Event (Option A)
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      activeTheme = e.target.value;
      filterCards();
    });
  }

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

  // Keyboard Shortcuts
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
      resetAllFilters();
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

// Text-to-Speech (TTS Audio Read-Aloud) Function
function speakText(text, lang = 'nl-NL') {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'en' ? 'en-US' : 'nl-NL';
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  } else {
    alert('Audio read-aloud is not supported on this browser.');
  }
}

// --- Simple feedback via the user's own email client ---
function buildMailto(subject, body) {
  return `mailto:${encodeURIComponent(REPORT_EMAIL)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function getRemainingCooldownSeconds() {
  const last = parseInt(localStorage.getItem(REPORT_COOLDOWN_KEY) || '0', 10);
  return Math.max(0, Math.ceil((REPORT_COOLDOWN_MS - (Date.now() - last)) / 1000));
}

function startCooldown() {
  localStorage.setItem(REPORT_COOLDOWN_KEY, Date.now().toString());
}

function initReportForms() {
  document.querySelectorAll('.report-form').forEach((form) => {
    const subject = form.dataset.subject || 'Feedback Utrecht Beslist';
    const sendLabel = form.dataset.sendLabel || 'Send email';
    const waitTemplate = form.dataset.waitMsg || 'Wait %s seconds';
    const cooldownMsg = form.dataset.cooldownMsg || 'Please wait before sending again.';
    const submitBtn = form.querySelector('.report-submit-btn');
    const honeypot = form.querySelector('.report-honeypot');

    function updateButton() {
      if (!submitBtn) return;
      const remaining = getRemainingCooldownSeconds();
      if (remaining > 0) {
        submitBtn.disabled = true;
        submitBtn.textContent = waitTemplate.replace('%s', remaining);
      } else {
        submitBtn.disabled = false;
        submitBtn.textContent = sendLabel;
      }
    }

    updateButton();
    setInterval(updateButton, 1000);

    form.addEventListener('submit', (e) => {
      e.preventDefault();

      // Very basic bot trap: if the hidden field is filled, do nothing
      if (honeypot && honeypot.value.trim()) return;

      const remaining = getRemainingCooldownSeconds();
      if (remaining > 0) {
        alert(cooldownMsg);
        return;
      }

      const textarea = form.querySelector('.report-textarea');
      const message = textarea.value.trim();
      if (!message) return;

      startCooldown();
      const body = `${message}\n\n---\n${window.location.href}`;
      window.location.href = buildMailto(subject, body);
      updateButton();
    });
  });
}

function openReportMailto(title, docId, subject) {
  const remaining = getRemainingCooldownSeconds();
  if (remaining > 0) {
    const form = document.querySelector('.report-form');
    const cooldownMsg = form?.dataset.cooldownMsg || 'Please wait before sending again.';
    alert(cooldownMsg);
    return;
  }

  const pageLabel = title ? `${title}${docId ? ' (#' + docId + ')' : ''}` : '';
  const body = `${pageLabel}\n\n${window.location.href}`;
  startCooldown();
  window.location.href = buildMailto(subject || 'Feedback Utrecht Beslist', body);
}

document.addEventListener('DOMContentLoaded', initReportForms);
