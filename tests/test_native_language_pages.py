"""Render smoke tests for the native-language (L1) picker UI (TASK-619).

These don't drive a real browser — they render the actual Jinja templates
through the Flask test client (route + base.html + extends), which catches
template syntax errors and confirms the new picker markup is present and
wired to the right endpoints/i18n keys. Full interactive click-through
(real login + live PATCH round-trip) is a manual step on top of this.
"""


class TestOnboardingNativePicker:
    """GET /welcome renders onboarding.html with the L1 picker."""

    def test_welcome_renders_native_picker(self, client):
        resp = client.get('/welcome')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # The three selectable cards, one per supported language id.
        assert 'native-language-card' in html
        assert 'data-id="1"' in html and 'data-id="2"' in html and 'data-id="3"' in html
        # i18n hook for the prompt copy.
        assert 'onboarding.native_title' in html
        # Persists server-side, not via localStorage.
        assert '/api/users/native-language' in html


class TestProfileNativeField:
    """GET /profile renders profile.html with the native-language setting."""

    def test_profile_renders_native_section(self, client):
        resp = client.get('/profile')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'nativeLanguageSection' in html
        assert 'nativeLanguageCards' in html
        assert 'profile.native_title' in html
        assert '/api/users/native-language' in html
