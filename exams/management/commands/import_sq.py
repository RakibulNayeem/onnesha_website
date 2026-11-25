"""Load short questions (SQ) from a transcribed data file (see exams/data/ssc_math/sq*.txt).

    python manage.py import_sq exams/data/ssc_math/sq02.txt

Same @headers as import_bank (@track, @subject, @chapter, @bank, @reserved). One line per question:
    no || refs (as printed) || question || solution (may be empty)      (¶ = line break)
Safe to re-run: an SQ is matched by subject + chapter + question text.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.management.commands.import_bank import GENERAL_BANK, SEP, bank_for
from exams.models import Chapter, Question, Source, Subject, Track


class Command(BaseCommand):
    help = "Import transcribed short questions from a data file."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+")

    @transaction.atomic
    def handle(self, *args, **opts):
        total = 0
        for path in opts["files"]:
            head, rows = {}, []
            for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("@"):
                    k, _, v = line[1:].partition(" ")
                    head[k] = v.strip()
                else:
                    f = [x.strip() for x in line.split("||")]
                    if len(f) != 4 or not f[2]:
                        raise CommandError(f"{path}:{n}: expected 'no{SEP}refs{SEP}question{SEP}solution'")
                    rows.append(f)
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
            reserved = head.get("reserved") == "1"
            for _no, refs, text, solution in rows:
                name, year, kind = (head["bank"], 2026, "other") if "bank" in head else bank_for(refs) or (GENERAL_BANK, 2026, "other")
                source, _ = Source.objects.get_or_create(name=name, defaults={"kind": kind, "year": year})
                Question.objects.update_or_create(
                    subject=subject, chapter=chapter, text=text.replace(" ¶ ", "\n"), qtype=Question.SQ,
                    defaults=dict(source=source, refs=refs, explanation=solution.replace(" ¶ ", "\n"),
                                  status=Question.APPROVED, reserved=reserved))
            total += len(rows)
            self.stdout.write(f"{path}: {len(rows)} SQs -> {subject.name} / {cname}")
        self.stdout.write(self.style.SUCCESS(f"done: {total} SQs imported"))
