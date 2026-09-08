from django import template

from ..i18n import t as translate

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, key):
    """{% t "apply_now" %} - a fixed interface word in the current language."""
    return translate(key, context.get("LANG", "en"))


@register.filter
def bl(obj, base):
    """{{ notice|bl:"title" }} - picks title_bn or title_en, with fallback."""
    if obj is None:
        return ""
    lang = getattr(obj, "_lang", None) or "en"
    if hasattr(obj, "pick"):
        return obj.pick(base, lang)
    return getattr(obj, f"{base}_en", "") or ""


@register.simple_tag(takes_context=True)
def bt(context, obj, base):
    """{% bt notice "title" %} - same as `bl` but knows the current language."""
    if obj is None:
        return ""
    lang = context.get("LANG", "en")
    if hasattr(obj, "pick"):
        return obj.pick(base, lang)
    bn = getattr(obj, f"{base}_bn", "") or ""
    en = getattr(obj, f"{base}_en", "") or ""
    return (bn or en) if lang == "bn" else (en or bn)


@register.filter
def get_item(d, key):
    try:
        return d.get(key, "")
    except AttributeError:
        return ""
