from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save


class ExamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "exams"

    def ready(self):
        from django.conf import settings
        from .roles import sync_roles

        def _sync(sender, **kw):
            sync_roles()

        def _profile(sender, instance, created, **kw):
            if created:
                from .models import Profile
                Profile.objects.get_or_create(user=instance)

        post_migrate.connect(_sync, sender=self, dispatch_uid="exams_sync_roles")
        post_save.connect(_profile, sender=settings.AUTH_USER_MODEL, dispatch_uid="exams_profile")
