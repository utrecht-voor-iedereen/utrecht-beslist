/**
 * Client-side interaction, search, dark mode, keyboard shortcuts, TTS audio & sharing for Utrecht Beslist
 */

// Rendered per page by base.html. The fallback keeps the file usable if the
// block is missing, but every published page carries it.
const UB = (() => {
  const fallback = {
    postal_badge: '📍 Postcode {code} → district {wijk}',
    results_one: 'decision',
    results_many: 'decisions',
    copied_to_clipboard: 'Link copied to clipboard!',
    tts_unsupported: 'Read-aloud is not supported by this browser.',
    theme_to_dark: '🌙 Dark',
    theme_to_light: '☀️ Light',
    lang: 'nl',
    speech: 'nl-NL'
  };
  const el = document.getElementById('ub-i18n');
  if (!el) return fallback;
  try {
    return Object.assign(fallback, JSON.parse(el.textContent));
  } catch (err) {
    return fallback;
  }
})();

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
      themeToggleBtn.textContent = newTheme === 'dark' ? UB.theme_to_light : UB.theme_to_dark;
    });

    const initialTheme = localStorage.getItem('utrecht_theme') || 'light';
    themeToggleBtn.textContent = initialTheme === 'dark' ? UB.theme_to_light : UB.theme_to_dark;
  }



  // Postal Code Lookup
  function checkPostalCode(query) {
    const match = query.match(/\b(35\d{2})\b/);
    if (match && UTRECHT_POSTAL_MAP[match[1]]) {
      detectedWijk = UTRECHT_POSTAL_MAP[match[1]];
      if (postalBadge) {
        postalBadge.style.display = 'inline-block';
        postalBadge.textContent = UB.postal_badge
          .replace('{code}', match[1])
          .replace('{wijk}', detectedWijk);
      }
    } else {
      detectedWijk = '';
      if (postalBadge) {
        postalBadge.style.display = 'none';
      }
    }
  }

  /* ── Guardados y estado en la URL ──────────────────────────────────────
     Dos cosas que van juntas: poder marcar lo que te interesa, y poder mandar
     por WhatsApp lo que estás viendo. Sin lo segundo, un filtro solo sirve
     mientras tienes la pestaña abierta. */
  const FAV_KEY = 'utrecht_favorites';
  const onlyFavsBtn = document.getElementById('only-favs-btn');
  const favCountEl = document.getElementById('fav-count');
  let onlyFavs = false;

  function readFavs() {
    try {
      const raw = JSON.parse(localStorage.getItem(FAV_KEY) || '[]');
      return Array.isArray(raw) ? raw.map(String) : [];
    } catch {
      // Modo privado o almacenamiento bloqueado: la página sigue funcionando
      // sin guardados en vez de romperse al arrancar.
      return [];
    }
  }

  function writeFavs(list) {
    try {
      localStorage.setItem(FAV_KEY, JSON.stringify(list));
    } catch { /* sin almacenamiento: dura lo que la pestaña */ }
  }

  function paintFavs() {
    const favs = readFavs();
    document.querySelectorAll('[data-fav]').forEach(btn => {
      const on = favs.includes(String(btn.dataset.fav));
      btn.textContent = on ? '★' : '☆';
      btn.classList.toggle('on', on);
      btn.setAttribute('aria-pressed', String(on));
      const label = on ? UB.unsave_decision : UB.save_decision;
      if (label) {
        btn.setAttribute('aria-label', label);
        btn.setAttribute('title', label);
      }
    });
    if (favCountEl) favCountEl.textContent = favs.length ? `(${favs.length})` : '';
    // El botón solo aparece cuando hay algo que enseñar.
    if (onlyFavsBtn) onlyFavsBtn.style.display = favs.length ? 'inline-flex' : 'none';
    if (!favs.length && onlyFavs) {
      onlyFavs = false;
      onlyFavsBtn?.setAttribute('aria-pressed', 'false');
      onlyFavsBtn?.classList.remove('active');
    }
  }

  // Delegado: las tarjetas no se repintan, pero la estrella vive dentro del
  // enlace al detalle y hay que impedir que el click navegue.
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-fav]');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const id = String(btn.dataset.fav);
    const favs = readFavs();
    const i = favs.indexOf(id);
    if (i >= 0) favs.splice(i, 1); else favs.push(id);
    writeFavs(favs);
    paintFavs();
    if (onlyFavs) filterCards();
  });

  if (onlyFavsBtn) {
    onlyFavsBtn.addEventListener('click', () => {
      onlyFavs = !onlyFavs;
      onlyFavsBtn.setAttribute('aria-pressed', String(onlyFavs));
      onlyFavsBtn.classList.toggle('active', onlyFavs);
      filterCards();
      syncUrl();
    });
  }

  /* El estado de los filtros viaja en la URL para que un enlace se pueda
     compartir y para que el botón de atrás no pierda lo que estabas mirando.
     `replaceState` y no `pushState`: teclear en el buscador crearía una entrada
     de historial por letra. */
  function syncUrl() {
    const p = new URLSearchParams();
    if (activeWijk !== 'all') p.set('wijk', activeWijk);
    if (activeTheme !== 'all') p.set('thema', activeTheme);
    if (activeHumanImpactGroup !== 'all') p.set('impact', activeHumanImpactGroup);
    if (searchQuery) p.set('q', searchQuery);
    if (onlyFavs) p.set('bewaard', '1');
    const qs = p.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
  }

  function readUrl() {
    const p = new URLSearchParams(location.search);
    const wijk = p.get('wijk');
    const thema = p.get('thema');
    const impact = p.get('impact');
    const q = p.get('q');

    // Solo se aceptan valores que existen en los desplegables: un parámetro
    // inventado dejaría la página en blanco sin decir por qué.
    if (wijk && wijkSelect && [...wijkSelect.options].some(o => o.value === wijk)) {
      activeWijk = wijk;
      wijkSelect.value = wijk;
    }
    if (thema && themeSelect && [...themeSelect.options].some(o => o.value === thema)) {
      activeTheme = thema;
      themeSelect.value = thema;
    }
    if (impact && HUMAN_IMPACT_THEMES[impact]) {
      activeHumanImpactGroup = impact;
      humanImpactBtns.forEach(b => b.classList.remove('active'));
      document.querySelector(`.human-impact-btn[data-impact-group="${impact}"]`)?.classList.add('active');
    }
    if (q) {
      searchQuery = q.toLowerCase().trim();
      if (searchInput) searchInput.value = q;
    }
    if (p.get('bewaard') === '1' && readFavs().length) {
      onlyFavs = true;
      onlyFavsBtn?.setAttribute('aria-pressed', 'true');
      onlyFavsBtn?.classList.add('active');
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

    onlyFavs = false;
    onlyFavsBtn?.setAttribute('aria-pressed', 'false');
    onlyFavsBtn?.classList.remove('active');

    filterCards();
    syncUrl();
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

      const matchesFav = !onlyFavs || readFavs().includes(String(card.dataset.doc));

      if (matchesTheme && matchesHumanImpact && matchesWijk && matchesSearch && matchesFav) {
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
      resultsCounterBadge.textContent =
        `${visibleCount} ${visibleCount === 1 ? UB.results_one : UB.results_many}`;
    }

    // Toggle Reset Button
    const isFiltered = (activeTheme !== 'all' || activeHumanImpactGroup !== 'all' || activeWijk !== 'all' || searchQuery !== '' || onlyFavs);
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
      syncUrl();
    });
  }

  // Human Impact Group Buttons Event
  humanImpactBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      humanImpactBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeHumanImpactGroup = btn.dataset.impactGroup || 'all';
      filterCards();
      syncUrl();
    });
  });

  // Wijk Select Event (Option A)
  if (wijkSelect) {
    wijkSelect.addEventListener('change', (e) => {
      activeWijk = e.target.value;
      filterCards();
      syncUrl();
    });
  }

  // Theme Select Event (Option A)
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      activeTheme = e.target.value;
      filterCards();
      syncUrl();
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

  // Read-aloud and share buttons carry their text in data attributes, so a
  // quote in a summary can no longer break the handler.
  document.addEventListener('click', (e) => {
    const speaker = e.target.closest('[data-speak]');
    if (speaker) {
      speakText(speaker.dataset.speak);
      return;
    }
    const sharer = e.target.closest('[data-share-title]');
    if (sharer) {
      shareCard(sharer.dataset.shareTitle, sharer.dataset.shareUrl);
      return;
    }
    const reporter = e.target.closest('[data-report-title]');
    if (reporter) {
      openReportMailto(
        reporter.dataset.reportTitle,
        reporter.dataset.reportDoc,
        reporter.dataset.reportSubject
      );
    }
  });

  // Arranque: pintar guardados, aplicar lo que venga en la URL y filtrar una
  // vez. El orden importa: readUrl() mira si hay guardados para aceptar
  // ?bewaard=1, así que paintFavs() va primero.
  paintFavs();
  readUrl();
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
    alert(UB.copied_to_clipboard);
  }
}

// Text-to-Speech (TTS Audio Read-Aloud) Function.
// The voice used to be nl-NL for everything except English, so the Turkish and
// Portuguese pages were read aloud by a Dutch voice.
function speakText(text) {
  if (!('speechSynthesis' in window)) {
    alert(UB.tts_unsupported);
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = UB.speech;
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
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
