from .i18n import STRINGS
from .models import SiteSettings


PUB_NAV = {
    "pub_home": "home",
    "pub_programs": "programs",
    "pub_teachers": "teachers",
    "pub_notices": "notices", "pub_notice_detail": "notices",
    "pub_results": "results", "pub_result_detail": "results",
    "pub_gallery": "gallery", "pub_videos": "videos",
    "pub_downloads": "downloads",
    "pub_blog": "blog", "pub_blog_detail": "blog",
    "pub_admission": "admission", "pub_contact": "contact",
    "pub_about": "about",
}


def site(request):
    lang = request.session.get("lang", "en")
    if lang not in ("en", "bn"):
        lang = "en"
    name = getattr(getattr(request, "resolver_match", None), "url_name", "")
    ctx = {}
    if name in PUB_NAV:
        ctx["nav"] = PUB_NAV[name]
    ctx.update({
        "LANG": lang,
        "IS_BN": lang == "bn",
        "site": SiteSettings.load(),
        "T": {k: (v[1] if lang == "bn" else v[0]) for k, v in STRINGS.items()},
    })
    return ctx
