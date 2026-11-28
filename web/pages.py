"""HTML page routes. Pages are client-side rendered: each route only serves its template."""

from flask import redirect, render_template, url_for

# (rule, endpoint, template). Endpoint names are referenced by url_for in templates.
PAGES = (
    ('/login', 'login', 'login.html'),
    ('/signup', 'signup', 'login.html'),
    ('/welcome', 'welcome', 'onboarding.html'),
    ('/language-selection', 'language_selection', 'language_selection.html'),
    ('/tests', 'tests', 'test_list.html'),
    ('/profile', 'profile', 'profile.html'),
    ('/study-plan', 'study_plan_page', 'study_plan.html'),
    ('/session', 'study_session_page', 'study_session.html'),
    ('/test/<slug>/preview', 'test_preview', 'test_preview.html'),
    ('/test/<slug>/prestudy', 'test_prestudy_page', 'test_prestudy.html'),
    ('/test/<slug>', 'test_page', 'test.html'),
    ('/test/<slug>/pinyin', 'pinyin_test_page', 'test_pinyin.html'),
    ('/test/<slug>/pitch-accent', 'pitch_accent_test_page', 'test_pitch_accent.html'),
    ('/test/<slug>/dictation', 'dictation_test_page', 'test_dictation.html'),
    ('/flashcards', 'flashcards', 'flashcards.html'),
    ('/word-list', 'word_list_page', 'word_list.html'),
    ('/calibration', 'calibration_page', 'calibration.html'),
    # Always on for zh, en and ja; the API answers 404 for any other language.
    ('/placement', 'placement_page', 'placement.html'),
    ('/classifier-drill', 'classifier_drill_page', 'classifier_drill.html'),
    ('/counter-drill', 'counter_drill_page', 'counter_drill.html'),
    ('/particle-drill', 'particle_drill_page', 'particle_drill.html'),
    ('/conjugation-drill', 'conjugation_drill_page', 'conjugation_drill.html'),
    ('/reading-drill', 'reading_drill_page', 'reading_drill.html'),
    # Grammar drills, one page per study language. Both keep progress through
    # routes/grammar_drill.py (/api/grammar-drill: shared daily + state tables).
    #   zh: static/data/grammar/zh, static/js/grammar/
    #   ja: the grammar course of the particle drill (data/particle_drill/ja-grammar)
    ('/grammar-drill/zh', 'grammar_drill_zh_page', 'grammar_drill_zh.html'),
    ('/grammar-drill/ja', 'grammar_drill_ja_page', 'grammar_drill_ja.html'),
    # The address without a language sends the browser to its study language's page.
    ('/grammar-drill', 'grammar_drill_page', 'grammar_drill.html'),
    # Idiom trainer, one page per study language (static/data/idioms/<lang>); progress
    # through the same tracking, as topics idiom-<id>.
    ('/idiom-trainer/zh', 'idiom_trainer_zh_page', 'idiom_trainer_zh.html'),
    ('/idiom-trainer/ja', 'idiom_trainer_ja_page', 'idiom_trainer_ja.html'),
    ('/idiom-trainer', 'idiom_trainer_page', 'idiom_trainer.html'),
    ('/dual-translation', 'dual_translation_page', 'dual_translation.html'),
    ('/dual-translation/profile', 'dual_translation_profile_page', 'dual_translation_profile.html'),
    # Knowledge Report ("My vocabulary"); always on.
    ('/knowledge', 'knowledge_page', 'knowledge.html'),
    ('/admin/vocab-preview', 'admin_vocab_preview', 'admin_vocab_preview.html'),
)

# (rule, endpoint) pairs that redirect to the login page.
LOGIN_REDIRECTS = (
    ('/', 'index'),
    ('/logout', 'logout'),
)


def _page_view(endpoint, template):
    def view(**_url_values):
        return render_template(template)
    view.__name__ = endpoint
    return view


def _login_redirect_view(endpoint):
    def view():
        return redirect(url_for('login'))
    view.__name__ = endpoint
    return view


def register_pages(app):
    for rule, endpoint in LOGIN_REDIRECTS:
        app.add_url_rule(rule, endpoint, _login_redirect_view(endpoint))
    for rule, endpoint, template in PAGES:
        app.add_url_rule(rule, endpoint, _page_view(endpoint, template))
