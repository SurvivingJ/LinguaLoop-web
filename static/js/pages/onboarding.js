// Native-language picker. Selection is optional — leaving it unset keeps
// native_language_id NULL, which is a legitimate state (Dual Translation
// falls back to English). We persist server-side rather than to
// localStorage: the target-study-language picker on the next page owns
// localStorage; native language (L1) is a distinct concept.
let selectedNativeLanguageId = null;
const nativeCards = document.querySelectorAll('.native-language-card');
function selectNativeCard(card) {
  nativeCards.forEach((c) => {
    c.classList.remove('selected');
    c.setAttribute('aria-checked', 'false');
  });
  card.classList.add('selected');
  card.setAttribute('aria-checked', 'true');
  selectedNativeLanguageId = parseInt(card.dataset.id, 10);
}
nativeCards.forEach((card) => {
  card.addEventListener('click', () => selectNativeCard(card));
  card.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      selectNativeCard(card);
    }
  });
});

// When the first-time user clicks "Get Started", flip the has_seen_welcome
// flag server-side so we don't show this page on their next login. Don't
// block navigation on the network call — worst case they see this page
// one extra time.
document.getElementById('get-started-btn').addEventListener('click', function (e) {
  e.preventDefault();
  const go = () => {
    window.location.href = '/language-selection';
  };

  // Persist the chosen native language (fire-and-forget — navigation is
  // gated on mark-welcome-seen below, not on this). Skip entirely if the
  // user didn't pick one, leaving native_language_id NULL.
  if (selectedNativeLanguageId && typeof window.authFetch === 'function') {
    window
      .authFetch('/api/users/native-language', {
        method: 'PATCH',
        body: JSON.stringify({ language_id: selectedNativeLanguageId }),
      })
      .catch((err) => console.error('set native-language failed:', err));
  }

  // Optimistically update cached user_data so a refresh of /welcome
  // doesn't strand them here.
  try {
    const store = sessionStorage.getItem('user_data') ? sessionStorage : localStorage;
    const raw = store.getItem('user_data');
    if (raw) {
      const parsed = JSON.parse(raw);
      parsed.hasSeenWelcome = true;
      store.setItem('user_data', JSON.stringify(parsed));
    }
  } catch (_) {
    /* non-fatal */
  }

  if (typeof window.authFetch !== 'function') {
    go();
    return;
  }
  window
    .authFetch('/api/auth/mark-welcome-seen', { method: 'POST' })
    .catch((err) => console.error('mark-welcome-seen failed:', err))
    .finally(go);
});
