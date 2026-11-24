import hashlib
from functools import lru_cache

from django import template

from exams.i18n import is_en, tr

register = template.Library()
_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_LETTERS = {"a": "ক", "b": "খ", "c": "গ", "d": "ঘ"}


@register.filter
def bn(value):
    """12 -> ১২ in Bangla; unchanged in English."""
    return str(value) if is_en() else str(value).translate(_DIGITS)


@register.filter
def bnletter(key):
    """'a' -> ক in Bangla, 'A' in English: the option labels."""
    return key.upper() if is_en() else _LETTERS.get(key, key)


@register.filter
def tile(pk):
    """Stable colour class t0..t9 for a tile, from its id."""
    return f"t{int(pk) % 10}"


@register.filter
def initial(name):
    """First letter of a name, for the watermark / badge."""
    return str(name).strip()[:1]


@register.simple_tag
def t(msg, **kw):
    """{% t "বাংলা লেখা" %} -> English when the interface is English. Extra keywords fill {placeholders}."""
    out = tr(msg)
    return out.format(**kw) if kw else out


@register.filter(name="tr")
def tr_filter(value):
    """Translate a Bangla label that comes from the database/choices, e.g. {{ t.get_kind_display|tr }}."""
    return tr(str(value))


@lru_cache(maxsize=None)
def _digest(path):
    from django.contrib.staticfiles import finders
    found = finders.find(path)
    if not found:
        return ""
    with open(found, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:10]


@register.simple_tag
def asset(path):
    """Static URL with a content hash, e.g. /static/css/site.css?v=ab12cd34ef.

    Static files are cached by browsers for a week under a fixed name, so without this a visitor
    can get new HTML with the previous stylesheet after a deploy. The hash changes with the file."""
    from django.templatetags.static import static
    v = _digest(path)
    return f"{static(path)}?v={v}" if v else static(path)
