"""Interface language (Bangla / English).

Bangla is the source language: templates and code contain the Bangla text, and EN maps it to English.
Anything missing from EN simply stays in Bangla, so a gap never breaks a page.
Question content is always shown as written in the book; only the interface is translated.
"""
from django.utils import translation
from django.utils.functional import lazy

LANGS = {"bn": "বাংলা", "en": "English"}


def is_en():
    return (translation.get_language() or "bn").startswith("en")


def tr(msg):
    """Translate one Bangla UI string for the active language."""
    from .i18n_en import EN
    return EN.get(msg, msg) if is_en() else msg


tr_lazy = lazy(tr, str)   # for labels defined at import time (form fields, choices)


def num(n):
    """12 -> ১২ in Bangla, 12 in English."""
    return str(n) if is_en() else str(n).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
