"""Load creative questions (CQ) from a transcribed data file (see exams/data/ssc_physics/cq*.txt).

    python manage.py import_cq exams/data/ssc_physics/cq01.txt

File format (same @headers as import_bank, including @bank, @reserved and an optional @chapter):
    Q no || refs || stem (¶ = line break)
    ক || marks || question || model answer (may be empty)
    খ || ...                      (up to four part lines, in order, follow each Q line)
Safe to re-run: a CQ is matched by subject + chapter + stem.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.management.commands.import_bank import GENERAL_BANK, SEP, bank_for
from exams.models import Chapter, Question, Source, Subject, Track

LETTERS = ["ক", "খ", "গ", "ঘ"]
BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


class Command(BaseCommand):
    help = "Import transcribed creative questions from a data file."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+")

    @transaction.atomic
    def handle(self, *args, **opts):
        total = 0
        for path in opts["files"]:
            head, cqs, cur = {}, [], None
            for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("@"):
                    k, _, v = line[1:].partition(" ")
                    head[k] = v.strip()
                elif line.startswith("Q "):
                    f = [x.strip() for x in line[2:].split("||")]
                    if len(f) != 3 or not f[2]:
                        raise CommandError(f"{path}:{n}: expected 'Q no{SEP}refs{SEP}stem'")
                    cur = dict(no=f[0], refs=f[1], stem=f[2].replace(" ¶ ", "\n"), parts=[], n=n)
                    cqs.append(cur)
                else:
                    f = [x.strip() for x in line.split("||")]
                    if cur is None or len(f) != 4 or f[0] not in LETTERS or f[0] != LETTERS[len(cur["parts"])]:
                        raise CommandError(f"{path}:{n}: bad part line (need ক/খ/গ/ঘ in order, 4 fields)")
                    cur["parts"].append({"q": f[2].replace(" ¶ ", "\n"), "marks": int(f[1].translate(BN)), "answer": f[3].replace(" ¶ ", "\n")})
            for need in ("track", "subject"):
                if need not in head:
                    raise CommandError(f"{path}: missing @{need} header")
            tslug, tname, tkind = head["track"].split(" ", 2)
            track, _ = Track.objects.get_or_create(slug=tslug, defaults={"name": tname, "kind": tkind})
            subject, _ = Subject.objects.get_or_create(track=track, name=head["subject"])
            chapter, cname = None, "(no chapter)"
            if "chapter" in head:
                order, cname = head["chapter"].split(" ", 1)
                chapter, _ = Chapter.objects.get_or_create(subject=subject, name=cname, defaults={"order": int(order)})
            reserved = head.get("reserved") == "1"   # @reserved 1 -> held back for self-test exams
            for c in cqs:
                if not c["parts"]:
                    raise CommandError(f"{path}:{c['n']}: Q{c['no']} has no parts")
                name, year, kind = (head["bank"], 2026, "other") if "bank" in head else bank_for(c["refs"]) or (GENERAL_BANK, 2026, "other")
                source, _ = Source.objects.get_or_create(name=name, defaults={"kind": kind, "year": year})
                Question.objects.update_or_create(
                    subject=subject, chapter=chapter, text=c["stem"], qtype=Question.CQ,
                    defaults=dict(source=source, refs=c["refs"], parts=c["parts"], status=Question.APPROVED, reserved=reserved))
            total += len(cqs)
            self.stdout.write(f"{path}: {len(cqs)} CQs -> {subject.name} / {cname}")
        self.stdout.write(self.style.SUCCESS(f"done: {total} CQs imported"))
