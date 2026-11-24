from django.utils import translation


class LanguageMiddleware:
    """Pick the interface language from the visitor's choice (cookie), default Bangla."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get("lang", "bn")
        lang = lang if lang in ("bn", "en") else "bn"
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        response = self.get_response(request)
        translation.deactivate()
        return response
