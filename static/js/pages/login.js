(function () {
  'use strict';

  // DOM Elements
  const emailStep = document.getElementById('email-step');
  const otpStep = document.getElementById('otp-step');
  const loading = document.getElementById('loading');
  const errorAlert = document.getElementById('error-alert');
  const errorMessage = document.getElementById('error-message');
  const emailInput = document.getElementById('email');
  const otpInput = document.getElementById('otp');
  const emailDisplay = document.getElementById('email-display');
  const emailForm = document.getElementById('email-form');
  const otpForm = document.getElementById('otp-form');
  const backBtn = document.getElementById('back-btn');
  const resendBtn = document.getElementById('resend-btn');

  // Utility Functions
  function showError(message) {
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function hideError() {
    errorAlert.classList.add('d-none');
    errorMessage.textContent = '';
  }

  function showLoading() {
    emailStep.classList.add('d-none');
    otpStep.classList.add('d-none');
    loading.classList.remove('d-none');
  }

  function hideLoading() {
    loading.classList.add('d-none');
  }

  function showEmailStep() {
    hideError();
    emailStep.classList.remove('d-none');
    otpStep.classList.add('d-none');
    hideLoading();
  }

  function showOtpStep() {
    hideError();
    emailStep.classList.add('d-none');
    otpStep.classList.remove('d-none');
    hideLoading();
    setTimeout(() => otpInput.focus(), 100);
  }

  // Silent device-restore on /login load. Users with a valid trusted-
  // device cookie (HttpOnly, invisible to JS) should skip OTP entirely.
  (async function autoRestoreOnLogin() {
    try {
      const r = await fetch('/api/auth/device-restore', {
        method: 'POST',
        credentials: 'same-origin',
      });
      if (!r.ok) return;
      const data = await r.json();
      if (!data.success || !data.jwt_token) return;
      localStorage.setItem('jwt_token', data.jwt_token);
      // Refresh token is an HttpOnly cookie set by the server.
      if (data.user) localStorage.setItem('user_data', JSON.stringify(data.user));
      window.location.href =
        data.user && data.user.hasSeenWelcome === false ? '/welcome' : '/language-selection';
    } catch (_) {
      /* stay on login form */
    }
  })();

  // Send OTP
  emailForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = emailInput.value.trim();

    if (!email || !emailInput.checkValidity()) {
      showError(LinguaI18n.t('login.error.invalid_email'));
      return;
    }

    hideError();
    showLoading();

    try {
      const response = await fetch('/api/auth/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          is_registration: true,
        }),
      });

      const data = await response.json();

      if (data.success) {
        emailDisplay.textContent = email;
        showOtpStep();
      } else {
        showEmailStep();
        showError(LinguaI18n.tError(data.error) || LinguaI18n.t('login.error.send_failed'));
      }
    } catch (error) {
      console.error('Send OTP error:', error);
      showEmailStep();
      showError(LinguaI18n.t('login.error.network'));
    }
  });

  // Verify OTP
  otpForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = emailInput.value.trim();
    const otp = otpInput.value.trim();

    if (otp.length !== 6) {
      showError(LinguaI18n.t('login.error.invalid_code'));
      return;
    }

    hideError();
    showLoading();

    try {
      const rememberDevice = document.getElementById('remember-device').checked;

      const response = await fetch('/api/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          email: email,
          otp_code: otp,
          remember_device: rememberDevice,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Persist to localStorage (survives browser restarts) whenever the
        // user asked to be remembered. We key off the checkbox intent — not
        // only the server's `remembered` flag — because the server sets a
        // persistent refresh cookie whenever remember was ticked, even if
        // issuing the trusted-device row degraded. Keeping the access token
        // in localStorage lets that persistent cookie silently renew it
        // after a restart. Unremembered logins use sessionStorage so they
        // vanish on tab close.
        const persist = data.remembered || rememberDevice;
        const store = persist ? localStorage : sessionStorage;
        const otherStore = persist ? sessionStorage : localStorage;
        // Clear the other tier so we never read a stale token from there.
        otherStore.removeItem('jwt_token');
        otherStore.removeItem('refresh_token');
        otherStore.removeItem('user_data');

        store.setItem('jwt_token', data.jwt_token);
        store.setItem('user_data', JSON.stringify(data.user));
        // Refresh token is an HttpOnly cookie set by verify-otp;
        // never stored in JS-readable storage.

        // Redirect first-time users to the welcome page; everyone else
        // goes straight to language selection. The flag is flipped to
        // true when the user clicks "Get Started" on the welcome page.
        if (!data.user.hasSeenWelcome) {
          window.location.href = '/welcome';
        } else {
          window.location.href = '/language-selection';
        }
      } else {
        showOtpStep();
        showError(
          LinguaI18n.tError(data.error || data.message) || LinguaI18n.t('login.error.verify_failed')
        );
        otpInput.value = '';
      }
    } catch (error) {
      console.error('Verify OTP error:', error);
      showOtpStep();
      showError(LinguaI18n.t('login.error.network'));
    }
  });

  // Back Button
  backBtn.addEventListener('click', function () {
    showEmailStep();
    otpInput.value = '';
  });

  // Resend OTP
  resendBtn.addEventListener('click', async function () {
    const email = emailInput.value.trim();

    this.disabled = true;
    this.textContent = LinguaI18n.t('login.sending');

    try {
      const response = await fetch('/api/auth/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          is_registration: true,
        }),
      });

      const data = await response.json();

      if (data.success) {
        hideError();
        // Visual feedback
        const infoAlert = otpStep.querySelector('.alert-info');
        infoAlert.style.animation = 'pulse 0.4s ease';
        setTimeout(() => (infoAlert.style.animation = ''), 400);
      } else {
        showError(LinguaI18n.tError(data.error) || LinguaI18n.t('login.error.resend_failed'));
      }
    } catch (error) {
      console.error('Resend OTP error:', error);
      showError(LinguaI18n.t('error.network'));
    } finally {
      this.disabled = false;
      this.textContent = LinguaI18n.t('login.resend');
    }
  });

  // Auto-format OTP input
  otpInput.addEventListener('input', function (e) {
    // Only allow numbers
    this.value = this.value.replace(/[^0-9]/g, '');

    // Auto-submit when 6 digits entered
    if (this.value.length === 6) {
      // Use requestSubmit for proper form submission
      if (otpForm.requestSubmit) {
        otpForm.requestSubmit();
      } else {
        // Fallback for older browsers
        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        otpForm.dispatchEvent(submitEvent);
      }
    }
  });

  // Build standalone language switcher (no navbar on login page)
  (function setupLoginLangSwitcher() {
    const container = document.getElementById('loginLangSwitcher');
    if (!container) return;
    const langs = LinguaI18n.SUPPORTED_LANGS;
    const current = LinguaI18n.currentLanguage();
    Object.keys(langs).forEach(function (code) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-outline-secondary' + (code === current ? ' active' : '');
      btn.textContent = langs[code].flag;
      btn.title = langs[code].nativeName;
      btn.addEventListener('click', function () {
        LinguaI18n.setLanguage(code);
        container.querySelectorAll('.btn').forEach(function (b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
      });
      container.appendChild(btn);
    });
  })();

  // If a token is already in storage, verify it before skipping the login
  // form — otherwise a stale token will bounce the user into a redirect
  // loop with any page whose 401 handler sends them back here.
  //
  // Mirrors the recovery sequence in window.authFetch (base.html):
  //   1. validate access token → if ok, go to /language-selection
  //   2. on 401, exchange the refresh token for a fresh access token
  //   3. only wipe storage and show the login form if both fail
  (async function checkExistingSession() {
    const accessToken = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
    if (!accessToken) return;
    try {
      const r = await fetch('/api/auth/profile', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (r.ok) {
        window.location.href = '/language-selection';
        return;
      }
      // Access token rejected — try the HttpOnly refresh cookie before
      // giving up. credentials:'include' sends the cookie; the server
      // rotates it and returns only the new access token.
      const refreshed = await fetch('/api/auth/refresh-token', {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshed.ok) {
        const data = await refreshed.json();
        // Write to whichever tier currently holds the (now-stale) token.
        const store = localStorage.getItem('jwt_token') ? localStorage : sessionStorage;
        store.setItem('jwt_token', data.jwt_token);
        window.location.href = '/language-selection';
        return;
      }
      // Both checks failed — wipe both tiers so we don't loop, and let the form render.
      ['jwt_token', 'refresh_token', 'user_data'].forEach(function (k) {
        localStorage.removeItem(k);
        sessionStorage.removeItem(k);
      });
    } catch (_) {
      /* offline / network issue — let the user log in */
    }
  })();
})();
