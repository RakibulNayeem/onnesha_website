"""Create the public-university question banks (listed A-Z on the Question bank page), with logos where we have them.

    python manage.py seed_universities

Safe to run again: it only creates missing banks and sets kind/logo. Logo files live in static/img/logos/.
"""
from django.core.management.base import BaseCommand

from exams.models import Source

UNIVERSITIES = [
    "ঢাকা বিশ্ববিদ্যালয়", "রাজশাহী বিশ্ববিদ্যালয়", "বাংলাদেশ কৃষি বিশ্ববিদ্যালয়", "বাংলাদেশ প্রকৌশল বিশ্ববিদ্যালয় (বুয়েট)",
    "চট্টগ্রাম বিশ্ববিদ্যালয়", "জাহাঙ্গীরনগর বিশ্ববিদ্যালয়", "ইসলামী বিশ্ববিদ্যালয়", "শাহজালাল বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়",
    "খুলনা বিশ্ববিদ্যালয়", "জাতীয় কবি কাজী নজরুল ইসলাম বিশ্ববিদ্যালয়", "বঙ্গবন্ধু শেখ মুজিবুর রহমান কৃষি বিশ্ববিদ্যালয়",
    "শেরেবাংলা কৃষি বিশ্ববিদ্যালয়", "হাজী মোহাম্মদ দানেশ বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়",
    "মাওলানা ভাসানী বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়", "পটুয়াখালী বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়",
    "যশোর বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়", "নোয়াখালী বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়", "পাবনা বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়",
    "জগন্নাথ বিশ্ববিদ্যালয়", "কুমিল্লা বিশ্ববিদ্যালয়", "বরিশাল বিশ্ববিদ্যালয়",
    "রাজশাহী প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয় (রুয়েট)", "চট্টগ্রাম প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয় (চুয়েট)",
    "খুলনা প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয় (কুয়েট)", "ঢাকা প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয় (ডুয়েট)", "বেগম রোকেয়া বিশ্ববিদ্যালয়",
    "বাংলাদেশ টেক্সটাইল বিশ্ববিদ্যালয়", "জাতীয় বিশ্ববিদ্যালয়", "বাংলাদেশ উন্মুক্ত বিশ্ববিদ্যালয়",
    "বঙ্গবন্ধু শেখ মুজিব মেডিকেল বিশ্ববিদ্যালয়", "চট্টগ্রাম ভেটেরিনারি ও অ্যানিমেল সায়েন্সেস বিশ্ববিদ্যালয়",
    "সিলেট কৃষি বিশ্ববিদ্যালয়", "বাংলাদেশ ইউনিভার্সিটি অব প্রফেশনালস", "রবীন্দ্র বিশ্ববিদ্যালয়, বাংলাদেশ",
    "বঙ্গবন্ধু শেখ মুজিবুর রহমান বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়", "বঙ্গবন্ধু শেখ মুজিবুর রহমান ডিজিটাল বিশ্ববিদ্যালয়",
    "রাঙ্গামাটি বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়", "বঙ্গবন্ধু শেখ মুজিবুর রহমান মেরিটাইম বিশ্ববিদ্যালয়",
    "হবিগঞ্জ কৃষি বিশ্ববিদ্যালয়", "শেখ হাসিনা বিশ্ববিদ্যালয়, নেত্রকোনা",
]

# Official emblems saved in static/img/logos/ (taken from each university's own website).
LOGOS = {
    "ঢাকা বিশ্ববিদ্যালয়": "du.png", "রাজশাহী বিশ্ববিদ্যালয়": "ru.png", "চট্টগ্রাম বিশ্ববিদ্যালয়": "cu.png",
    "জাহাঙ্গীরনগর বিশ্ববিদ্যালয়": "ju.png", "জগন্নাথ বিশ্ববিদ্যালয়": "jnu.png", "বাংলাদেশ কৃষি বিশ্ববিদ্যালয়": "bau.png",
    "হাজী মোহাম্মদ দানেশ বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়": "hstu.png", "নোয়াখালী বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়": "nstu.png",
    "পাবনা বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয়": "pust.png", "জাতীয় বিশ্ববিদ্যালয়": "nu.png",
    "চট্টগ্রাম প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয় (চুয়েট)": "cuet.png",
}


class Command(BaseCommand):
    help = "Create the university banks (A-Z list) with logos."

    def handle(self, *args, **opts):
        made = 0
        for name in UNIVERSITIES:
            src, created = Source.objects.get_or_create(name=name, defaults={"kind": "university"})
            made += created
            changed = []
            if src.kind != "university":
                src.kind = "university"; changed.append("kind")
            if LOGOS.get(name) and src.logo != LOGOS[name]:
                src.logo = LOGOS[name]; changed.append("logo")
            if changed:
                src.save(update_fields=changed)
        total = Source.objects.filter(kind="university").count()
        self.stdout.write(self.style.SUCCESS(f"{made} created; {total} universities, {Source.objects.filter(kind='university').exclude(logo='').count()} with a logo"))
