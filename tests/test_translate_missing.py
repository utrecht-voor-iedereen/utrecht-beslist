"""
Regression cover for the loop that stalled the nightly run.

The translator measured completeness against all ten fields even when the
summarizer had left some of them empty at the source. Fifteen of the twenty-nine
entries have no `key_figure`, so those language passes could never report ten of
ten: every one burned four attempts, was written down as incomplete, and came
back on the pending list the next night. The 31 July run spent fifteen minutes
on it and was cancelled before the commit.
"""
from __future__ import annotations

from scripts.translate_missing import (
    FIELDS,
    TARGETS,
    is_untranslated,
    missing_langs,
    translatable_fields,
)


def entry(**overrides):
    """An entry with every Dutch and English source filled in."""
    item = {}
    for base, nl_key, en_key in FIELDS:
        # Over 25 characters: is_untranslated() exempts anything shorter,
        # because a year or an amount is meant to come through identical.
        item[nl_key] = f"{base}: de tekst van de gemeenteraad over dit voorstel"
        item[en_key] = f"{base}: the council text about this particular proposal"
    item.update(overrides)
    return item


def translated(item, suffix):
    """Fills in every field the entry can actually produce, for one language."""
    for base, _nl, _en in translatable_fields(item):
        item[f"{base}_{suffix}"] = f"{base}: de vertaalde tekst voor {suffix} hier"
    return item


def test_fields_without_a_source_are_not_translatable():
    item = entry(cifra_clave_nl="", key_figure_en="")
    bases = [base for base, _nl, _en in translatable_fields(item)]
    assert "key_figure" not in bases
    assert len(bases) == len(FIELDS) - 1


def test_an_entry_missing_key_figure_can_still_be_finished():
    """The exact shape of the fifteen entries the run kept retrying."""
    item = entry(cifra_clave_nl="", key_figure_en="")
    for suffix in TARGETS:
        translated(item, suffix)
    assert missing_langs(item, force=False) == []


def test_a_field_that_has_a_source_but_no_translation_is_still_reported():
    item = entry()
    for suffix in TARGETS:
        translated(item, suffix)
    item["summary_de"] = ""
    assert missing_langs(item, force=False) == ["de"]


def test_blank_translations_of_translatable_fields_are_reported():
    item = entry()
    assert sorted(missing_langs(item, force=False)) == sorted(TARGETS)


def test_force_asks_for_every_language_regardless():
    item = entry()
    for suffix in TARGETS:
        translated(item, suffix)
    assert sorted(missing_langs(item, force=True)) == sorted(TARGETS)


def test_recheck_catches_an_english_echo():
    item = entry()
    for suffix in TARGETS:
        translated(item, suffix)
    item["summary_fr"] = item["summary_en"]
    assert missing_langs(item, force=False) == []
    assert missing_langs(item, force=False, recheck=True) == ["fr"]


def test_short_values_are_never_treated_as_untranslated():
    """An amount or a year is supposed to come through identical."""
    assert is_untranslated("2,497 miljoen euro", "2,497 miljoen euro", "2,497 miljoen euro") is False


def test_a_title_may_keep_its_dutch_name():
    dutch = "Vaststelling Meerjarenperspectief Ruimte 2026"
    assert is_untranslated(dutch, "Adoption of the Spatial Perspective", dutch, "title_short") is False
    assert is_untranslated(dutch, dutch, dutch, "summary") is True
