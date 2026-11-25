"""Load questions from a transcribed data file (see exams/data/ssc_physics/*.txt).

    python manage.py import_bank exams/data/ssc_physics/ch01.txt

Safe to run again: a question is matched by subject + chapter + text, so re-runs update instead of duplicating.
Each question goes into a bank named after the first board/year it carries (e.g. "ঢাকা বোর্ড ২০২৩").
Questions without a valid printed answer are skipped, never guessed.
Optional headers: "@bank NAME" puts every question in that bank; "@reserved 1" holds them back for self-test exams;
"@chapter" may be omitted (model tests span several chapters).
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.models import Chapter, Question, Source, Subject, Track

BOARDS = {"ঢা": "ঢাকা", "রা": "রাজশাহী", "কু": "কুমিল্লা", "য": "যশোর", "চ": "চট্টগ্রাম",
          "ব": "বরিশাল", "সি": "সিলেট", "দি": "দিনাজপুর", "ম": "ময়মনসিংহ", "মাদ্রাসা": "মাদ্রাসা", "মা": "মাদ্রাসা"}
BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
GENERAL_BANK = "উদ্ভাস এসএসসি প্রশ্নব্যাংক ২০২৬"
ANS = {"a", "b", "c", "d"}
SEP = " || "


TAG = re.compile(r"^\s*([^\s.\'’‘]+)\.?\s*(?:বো\.?)?\s*(?:[\'’‘]\s*([০-৯0-9]{2}))?\s*$")


def bank_for(refs):
    """First board+year in a reference string -> (bank name, year, 'board'), or None.

    "ঢা. বো.; ব. বো.'২৪; চ. বো.'২২" : a year applies to the boards listed before it, so the
    primary bank here is Dhaka 2024 (the first board named)."""
    pending, pairs = [], []
    for part in re.split(r"[;,]", refs):
        m = TAG.match(part.strip())
        if not m or m.group(1) not in BOARDS:
            continue
        pending.append(m.group(1))
        if m.group(2):
            pairs += [(b, 2000 + int(m.group(2).translate(BN))) for b in pending]
            pending = []
    if not pairs:
        return None
    board, year = pairs[0]
    bn_year = str(year).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    return f"{BOARDS[board]} বোর্ড {bn_year}", year, "board"


class Command(BaseCommand):
    help = "Import transcribed MCQs from a data file."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        total = skipped = 0
        for path in opts["files"]:
            head, rows = {}, []
            for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("@"):
                    k, _, v = line[1:].partition(" ")
                    head[k] = v.strip()
                else:
                    rows.append((n, line))
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
            kept = 0
            for n, line in rows:
                f = line.split(SEP)
                if len(f) != 8:
                    raise CommandError(f"{path}:{n}: expected 8 fields separated by '{SEP}', got {len(f)}")
                no, refs, ans, text, *opts_ = [x.strip() for x in f]
                if ans not in ANS or not all(opts_) or not text:
                    skipped += 1
                    self.stderr.write(f"skip {path}:{n} (Q{no}) - no valid answer/options")
                    continue
                text = text.replace(" ¶ ", "\n")
                found = bank_for(refs)
                name, year, kind = (head["bank"], 2026, "other") if "bank" in head else found or (GENERAL_BANK, 2026, "other")
                source, _ = Source.objects.get_or_create(name=name, defaults={"kind": kind, "year": year})
                if not opts["dry_run"]:
                    # The stem alone is not unique ("নিচের কোনটি মৌলিক রাশি?" appears twice with different
                    # options), so a question is identified by its stem and its four options together.
                    Question.objects.update_or_create(
                        subject=subject, chapter=chapter, text=text, qtype=Question.MCQ,
                        option_a=opts_[0], option_b=opts_[1], option_c=opts_[2], option_d=opts_[3],
                        defaults=dict(source=source, refs=refs, correct=ans, status=Question.APPROVED, reserved=reserved))
                kept += 1
            total += kept
            self.stdout.write(f"{path}: {kept} questions -> {subject.name} / {cname}")
        self.stdout.write(self.style.SUCCESS(f"done: {total} imported, {skipped} skipped"))
