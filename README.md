# Onnesha — Coaching Centre Finance & Management System

A Django admin application for running the money side of a coaching centre:
students, month-by-month enrollment, fee collection, dues, expenses, teacher
payments, attendance and reports.

Built for **অন্বেষা | Onnesha — একাডেমিক এন্ড এডমিশন কেয়ার**, Sherpur, Bogura.

---

## 1. Run it on your own computer (5 minutes)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows:  .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo         # optional: 20 fake students, 3 months of data
python manage.py runserver
```

Open <http://127.0.0.1:8000>.

`seed_demo` creates the first admin account:

| username | password |
|---|---|
| `admin` | `onnesha123` |

**Change that password immediately** (top-right → Django admin → Users), or skip
`seed_demo` and make your own account with `python manage.py createsuperuser`.

---

## 2. What is inside

### The idea behind the data
A student is registered **once**. What changes every month is the
**enrollment** — one row per student per month listing the subjects taken that
month. A student can take 3 subjects in September, 4 in October, none in
November and 2 again in December. No enrollment row for a month means that
student studied nothing and is charged nothing. Every fee, due and report is
built on top of that one idea.

### Pages

| Page | What you do there |
|---|---|
| **Dashboard** | Pick a month: cash in, cash out, profit, fees charged vs collected, collection rate, batch-wise breakdown, teacher dues, last 6 months |
| **Enrollment** | The month's roll. Filter by batch or payment status. One button carries everyone forward from last month |
| **Collect fee** | Choose a student, the outstanding amount fills in, save and print a receipt |
| **Attendance** | Pick a batch and date, tick who is present |
| **Expenses** | Rent, printing, bills, publicity — with an optional batch tag |
| **Students** | Search by name, ID or phone; filter by batch, class, status. Each student has a page showing every month and every payment |
| **Teachers** | Fixed salary or a percentage share of what their courses collected. Recording a payment writes an expense automatically, so profit is never overstated |
| **All payments** | Every receipt, filterable by month, type or student. Two different views: money *received during* a month, and fees *for* a month |
| **Due list** | Everyone who owes money, with the guardian's phone number, exportable to CSV for your follow-up calls |
| **Monthly report** | Income by type, expense by category, course popularity — printable |
| **Courses & fees** | The price list: subject × class × programme × monthly fee |
| **Django admin** | Subjects, programmes, batches, users, website content, and raw access to everything |

### Programmes and classes
Out of the box: Academic, SSC Preparation, HSC Preparation, Admission Test —
across Class 6 to 12 plus an Admission Test level. Add or rename programmes in
the Django admin; the rest of the app follows.

### Student IDs
Generated as `ONS-26-0001` (prefix, two-digit year, running number). The field
is pre-filled on the form but you can type your own; the only rule is that it
must be unique. Change the prefix with the `STUDENT_ID_PREFIX` environment
variable.

### Teacher pay
Three modes: a fixed monthly amount, a percentage share of the fees collected
on that teacher's courses, or per-class (which you enter by hand). The Teachers
page shows what each teacher should get for a month, what has been paid and
what is still owed.

---

## 3. Deploying online

### The one thing that matters
**Do not use SQLite in the cloud.** Create a free Postgres database -
[Neon](https://neon.tech) or [Supabase](https://supabase.com) - and set
`DATABASE_URL`. The app reads it automatically. Strip `-pooler` from the Neon
hostname and remove `&channel_binding=require` from the end; psycopg2 does not
accept that parameter.

### Environment variables (both hosts)

```
SECRET_KEY=<a long random string>
DEBUG=False
ALLOWED_HOSTS=.onrender.com          (or .vercel.app)
CSRF_TRUSTED_ORIGINS=https://your-real-url
DATABASE_URL=postgresql://...?sslmode=require
TIME_ZONE=Asia/Dhaka
```

Generate a key with:
`python -c "import secrets; print(secrets.token_urlsafe(64))"`

### Option A - Render (recommended)
A normal long-running server, which is what Django expects.

1. Push this folder to GitHub.
2. [render.com](https://render.com) -> New -> Web Service -> pick the repo.
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   Start command: `python manage.py migrate && gunicorn onnesha_finance.wsgi`
4. Add the environment variables above. Deploy.
5. Open the Shell tab and run `python manage.py createsuperuser`.

Migrations run on every deploy, so you never do them by hand. The free tier
sleeps after 15 minutes idle and takes about 50 seconds to wake on the next
visit; the paid tier removes that.

`render.yaml` in this folder holds the same settings if you prefer a Blueprint.

### Option B - Vercel
`vercel.json` and `build_files.sh` are included.

Two things this project learned the hard way, already fixed here:
- Vercel treats a folder named `public/` as its static-assets directory, so a
  Django app cannot be called that. The website app is named `website`.
- Vercel's Python image is PEP 668 "externally managed", so `build_files.sh`
  installs with `--break-system-packages`.

1. Push to GitHub, import the repo in Vercel.
2. Add the environment variables above, with `ALLOWED_HOSTS=.vercel.app`.
3. Deploy.
4. Migrations do **not** run automatically. From your own computer:
   ```bash
   $env:DATABASE_URL="postgresql://..."     # PowerShell
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Backups
Export the database on a schedule. A coaching centre's fee history is not
something to lose. On Postgres: `pg_dump`. Locally: copy `db.sqlite3`.

## 4. Checking it still works after you change something

```bash
python check_app.py
```

This logs in, opens every page, creates a student, enrolls them, takes a part
payment, checks the due is right, tries a duplicate enrollment (must be
rejected), runs the carry-forward twice (must not duplicate) and checks a
teacher payment creates its expense. It prints `FAILURES: none` when the app is
healthy.

---

---

## 6. The public website

The project now has two halves sharing one database:

| URL | What it is | Who can see it |
|---|---|---|
| `/` | The public website | Everyone |
| `/manage/` | The finance system | Staff only, after login |
| `/django-admin/` | Content and raw data | Staff only |

### Pages on the public site
Home, Programs (with the real fee list), Teachers, Notices, Results, Gallery,
Video lectures, Downloads, Blog, Online admission form, Contact and About.

The home page opens with a **carousel**. Slides are managed in the admin under
**Hero slides** - each has a picture (upload or URL), a headline and subtitle in
both languages, and its own button text and link. Drag the order number to
reorder. Untick `is_published` to pull a slide without deleting it. If there
are no slides at all the page falls back to a plain gradient banner, so the
site never looks broken.

The programme cards on the home page are clickable and jump to that
programme's fee list on the Programs page.

**There is no staff-login link on the public site.** Staff go straight to
`/manage/` and the login form appears there. This is not real security - the
finance system is protected by the login itself, which is what actually keeps
it safe - but it keeps the staff area out of sight of casual visitors and
search engines.

### Two languages
Every page has an **EN / বাং** toggle in the navbar. Fixed interface words live
in `website/i18n.py` - one Python dictionary, edit it and the whole site
changes. Your own content (notices, blog posts, teacher bios) has two fields
each, `_bn` and `_en`; if you fill in only one, that one is shown in both
languages.

Django's usual translation machinery needs `.po` files compiled with gettext
tools, which are awkward to install on Windows. The dictionary approach does
the same job with no build step.

### Results
Two levels, as you asked for:

- **Merit list** - the public table: position, name, class, marks, grade.
- **Private lookup** - a student types their own ID and sees their
  subject-wise breakdown, percentage and grade, with a print button.

Two switches on each exam control this. `is_published` hides the whole exam
until you are ready. `show_public_list` lets you publish an exam for private
lookup only, with no public table. Nothing appears on the site until you tick
`is_published`, so you can enter marks over several days in peace.

To enter results: Django admin → Exams → add the exam → add each student's
total in the inline rows → save. Positions are calculated automatically, ties
share a position. For subject-wise marks, open Exam results → pick a student →
add each subject.

### Admission applications
The public form creates an **Admission application**, not a Student. They land
in the admin with a status you move through New → Contacted → Admitted. Keeping
them separate means a curious visitor filling in the form never touches your
fee records.

### Images and files on serverless hosting
Every image and file field comes in pairs: upload a file **or** paste a URL. On
Vercel uploaded files are wiped between requests, so use the URL field there -
a Facebook photo link, Google Drive, Imgur, anything public. On Render, uploads
work normally.

### Starter content

```bash
python manage.py seed_website
```

Creates site settings, three notices, sample videos, a gallery album, two blog
posts, downloads and one exam with results, so you can see every page working
before writing anything real.

### Checking the public site

```bash
python check_website.py
```

Opens every public page logged out, toggles Bengali, looks up a result, submits
the admission and contact forms, checks the spam trap, verifies an unpublished
exam returns 404, and confirms `/manage/` still demands a login.

### One privacy note
A public merit list puts students' names and marks on the open internet where
Google will index them. That was your choice and the code supports it, but if a
guardian ever objects, untick `show_public_list` on that exam and only the
private lookup remains.

---

## 7. Things deliberately left out

Being straight about the boundaries so you can plan:

- **No SMS or bKash API.** Payments are recorded by hand after you receive them.
  Adding an SMS due-reminder through a Bangladeshi gateway (Alpha SMS, BulkSMSBD)
  is a small addition on top of the due list.
- **No online payment link for guardians.** Same reason — that needs a merchant
  account and a payment gateway integration.
- **No student or guardian login.** Admin-only by design, which is what you
  asked for. A read-only guardian portal would be the natural next step.
- **No exam marks or result management.** This is a finance and enrollment
  system, not a full LMS.
- **Attendance is daily per batch**, not per subject period. If you teach the
  same batch different subjects on different days that still works; if you need
  subject-wise attendance it needs one extra field.
#   o n n e s h a _ w e b s i t e  
 