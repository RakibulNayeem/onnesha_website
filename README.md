# Onnesha Exam — অন্বেষা

MCQ / CQ practice, timed model tests and previous-year question banks for
SSC, HSC, university admission and jobs (Bangladesh curriculum). Django +
django-allauth (email, Google, Facebook sign-in).

## Run
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Content
Everything is managed in the Django admin (`/django-admin/`):
Track (SSC/HSC/Admission/Job) → Subject → Chapter, plus Source (a question
bank such as "DU 2022-23"). Questions are created as **Draft**; filter by
status in *Questions* and use the **Approve** action — only approved
questions reach students.

## Environment
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`,
and optionally `GOOGLE_CLIENT_ID/SECRET`, `FACEBOOK_CLIENT_ID/SECRET`
(redirect URL `https://<domain>/accounts/<google|facebook>/login/callback/`).
