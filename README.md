# 📋 Job Application Tracker

A small local web app to track your job applications **and store the exact
resume file you used for each company** — so when a recruiter calls, you can
instantly pull up the right resume version.

## Features

- Add applications with company, role, date, status, location, job link, and notes.
- **Attach the resume PDF you used** — stored as a real file, re-downloadable anytime.
- Move applications through stages: Applied → Online Assessment → Interview → Offer → Accepted / Rejected.
- **Follow-up reminders** — set a date to chase a reply; overdue ones are flagged at the top.
- Search by company/role and filter by status.
- At-a-glance metrics (total, interviews, offers, follow-ups due).
- Export everything to CSV.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`.

## Where your data lives

Everything stays **on your computer** — nothing is uploaded anywhere:

- `data/tracker.db` — the database of applications
- `data/resumes/` — the resume PDFs you attached

> The `data/` folder is git-ignored, so your applications and resumes are never
> committed to GitHub even if you push this project.

## Daily use

1. Run `streamlit run app.py`.
2. Use the **sidebar** to add each application as you apply, attaching that day's resume.
3. When you get a callback, search the company and **download the resume you used**.
4. Update the status as you move through interviews.
