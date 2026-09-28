"""
The About page states how the site works; every language must say all of it.
"""

from scripts.i18n import LANGUAGES, status_text, t
from scripts.over_content import OVER_HERO, OVER_SECTIONS, over_sections


def test_every_language_has_every_section():
    counts = {lang: [len(p) for _i, _t, p in OVER_SECTIONS[lang]] for lang in LANGUAGES}
    assert len(set(map(tuple, counts.values()))) == 1, counts
    assert set(OVER_HERO) >= set(LANGUAGES)


def test_labels_are_the_ones_the_site_shows():
    for lang in LANGUAGES:
        text = " ".join(p for _i, _t, paragraphs in over_sections(lang) for p in paragraphs)
        assert "{" not in text, lang
        assert status_text("agenda", lang) in text, lang
        assert status_text("passed", lang) in text, lang
        assert t("report_error", lang) in text, lang
