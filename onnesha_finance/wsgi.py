import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onnesha_finance.settings")

application = get_wsgi_application()
# Vercel's Python runtime looks for a callable named `app`.
app = application
