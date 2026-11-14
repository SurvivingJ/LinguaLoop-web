document.addEventListener('DOMContentLoaded', function () {
  const languageCards = document.querySelectorAll('.language-card');
  const continueBtn = document.getElementById('continue-btn');
  const browseTestsLink = document.getElementById('browse-tests-link');
  let selectedLanguage = null;

  // Fetch native names from metadata
  LinguaMetadata.load().then(function (meta) {
    if (!meta || !meta.languages) return;
    languageCards.forEach(function (card) {
      const langId = parseInt(card.dataset.id);
      const lang = meta.languages.find(function (l) {
        return l.id === langId;
      });
      if (lang && lang.native_name) {
        const nativeEl = card.querySelector('.language-native');
        if (nativeEl) nativeEl.textContent = lang.native_name;
      }
    });
  });

  // Handle language card selection
  languageCards.forEach((card) => {
    card.addEventListener('click', function () {
      // Remove selection from all cards
      languageCards.forEach((c) => {
        c.classList.remove('selected');
        c.querySelector('.check-icon').style.display = 'none';
      });

      // Add selection to clicked card
      this.classList.add('selected');
      this.querySelector('.check-icon').style.display = 'block';

      // Store selected language ID
      selectedLanguage = {
        id: parseInt(this.dataset.id),
      };

      // Enable continue button and the secondary browse-tests link
      continueBtn.disabled = false;
      if (browseTestsLink) {
        browseTestsLink.style.pointerEvents = 'auto';
        browseTestsLink.style.opacity = '1';
      }
    });
  });

  // Persist the chosen language (1=Chinese, 2=English, 3=Japanese) before
  // navigating, so both the daily session and the tests page see it.
  function persistSelectedLanguage() {
    if (selectedLanguage) {
      localStorage.setItem('selectedLanguageId', selectedLanguage.id.toString());
    }
  }

  // Primary CTA: start the daily study session.
  continueBtn.addEventListener('click', function () {
    if (selectedLanguage) {
      persistSelectedLanguage();
      window.location.href = continueBtn.dataset.sessionUrl;
    }
  });

  // Secondary CTA: browse tests. The href already points to the tests page;
  // this handler just persists the selection first (and no-ops until a
  // language is chosen, matching the disabled visual state).
  if (browseTestsLink) {
    browseTestsLink.addEventListener('click', function (e) {
      if (!selectedLanguage) {
        e.preventDefault();
        return;
      }
      persistSelectedLanguage();
    });
  }

  // Check if language was previously selected
  const savedLanguageId = localStorage.getItem('selectedLanguageId');
  if (savedLanguageId) {
    const savedCard = document.querySelector(`[data-id="${savedLanguageId}"]`);
    if (savedCard) {
      savedCard.click();
    }
  }
});
