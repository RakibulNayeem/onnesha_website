from django import template

register = template.Library()
_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_LETTERS = {"a": "ক", "b": "খ", "c": "গ", "d": "ঘ"}


@register.filter
def bn(value):
    """12 -> ১২ (Bangla digits)."""
    return str(value).translate(_DIGITS)


@register.filter
def bnletter(key):
    """'a' -> ক, the option labels Bangladeshi papers use."""
    return _LETTERS.get(key, key)


@register.filter
def tile(pk):
    """Stable colour class t0..t9 for a tile, from its id."""
    return f"t{int(pk) % 10}"


@register.filter
def initial(name):
    """First letter of a name, for the watermark / badge."""
    return str(name).strip()[:1]
