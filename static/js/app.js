/**
 * Client-side interaction, search, postal code lookup & sharing for Utrecht Beslist
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

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-input');
  const filterChips = document.querySelectorAll('.filter-chip');
  const cards = document.querySelectorAll('.card');
  const langBtns = document.querySelectorAll('.lang-btn');
  const postalBadge = document.getElementById('postal-badge');
  const mapPaths = document.querySelectorAll('.wijk-map-path');

  let activeTheme = 'all';
  let activeWijk = 'all';
  let searchQuery = '';
  let detectedWijk = '';

  // Language Switcher Logic
  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetLang = btn.dataset.lang;
      const currentPath = window.location.pathname;
      
      if (targetLang === 'en' && currentPath.includes('/nl/')) {
        window.location.href = currentPath.replace('/nl/', '/en/');
      } else if (targetLang === 'nl' && currentPath.includes('/en/')) {
        window.location.href = currentPath.replace('/en/', '/nl/');
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

      const matchesTheme = (activeTheme === 'all' || cardTheme.includes(activeTheme) || tagsText.includes(activeTheme));
      
      const targetWijk = activeWijk !== 'all' ? activeWijk.toLowerCase() : (detectedWijk ? detectedWijk.toLowerCase() : '');
      const matchesWijk = !targetWijk || cardWijk.includes(targetWijk) || tagsText.includes(targetWijk);

      const matchesSearch = !searchQuery || titleText.includes(searchQuery) || summaryText.includes(searchQuery) || tagsText.includes(searchQuery);

      if (matchesTheme && matchesWijk && matchesSearch) {
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
      checkPostalCode(searchQuery);
      filterCards();
    });
  }

  // Theme Filter Chips Event
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
