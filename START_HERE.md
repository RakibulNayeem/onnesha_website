# Onnesha — start here

Two halves, one project, one database:

| URL | What | Who |
|---|---|---|
| `/` | Public website | Everyone |
| `/manage/` | Finance system | Staff, after login |
| `/django-admin/` | Content and raw data | Staff |

---

## 1. Run it on your computer

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py seed_website
python manage.py runserver
```

Open http://127.0.0.1:8000 — login `admin` / `onnesha123`.

The two seed commands fill the database with fake students and sample website
content so every page has something to show. Skip them and run
`python manage.py createsuperuser` instead if you want to start empty.

`seed_demo` must run before `seed_website` — the programmes and courses come
from the first, and the second adds Bengali names and website flags to them.

---

## 2. Put it on GitHub

Create a new **private** repo on github.com — empty, no README, no .gitignore.

```powershell
git init
git branch -M main
git add .
git status
```

Check `git status` does **not** list `db.sqlite3`, `.venv`, `.env` or `media`.
The `.gitignore` keeps them out. Then:

```powershell
git commit -m "Onnesha coaching centre system"
git remote add origin https://github.com/YOUR-NAME/YOUR-REPO.git
git push -u origin main
```

Every change after that:

```powershell
git add .
git commit -m "what you changed"
git push
```

---

## 3. Put it online

See section 3 of README.md. Short version: create a free Neon Postgres
database, then deploy to Render with the environment variables listed there.
Render runs migrations for you on each deploy.

---

## 4. First things to set up

Log in at `/django-admin/` and fill these in, in order:

1. **Programs** — Academic, SSC Preparation, and so on. Tick *Show on website*,
   add the Bengali name and tagline.
2. **Subjects** — Physics, Chemistry, Higher Math…
3. **Batches** — your timetable groups.
4. **Courses** — subject × class × programme, each with its real monthly fee.
   This is the price list everything else adds up from.
5. **Teachers** — tick *Show on website* and fill the profile section for
   anyone who should appear publicly.
6. **Site settings** — address, phone, hero text, social links.
7. **Hero slides** — the carousel on the home page. Use real photos of your
   centre; paste image URLs rather than uploading if you are on Vercel.

Then add students at `/manage/students/`, enroll them for the month at
`/manage/enrollment/`, and collect fees at `/manage/fees/collect/`.

---

## 5. Checking nothing is broken

```powershell
python check_app.py       # the finance system
python check_website.py   # the public site
```

Both print `FAILURES: none` when healthy.
