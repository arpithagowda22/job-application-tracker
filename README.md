# 🎯 Job Application Tracker

A premium, animated job-application tracker that stores **the exact resume PDF
you used for each company** — so when a recruiter calls, you pull up the right
version in one click.

Built as a custom web app: a **Flask** backend (REST API + SQLite + on-disk
resume storage) with a **bespoke animated front-end** (HTML / CSS / vanilla JS)
— aurora background, glassmorphism cards, smooth motion, and confetti when you
land an offer.

## Features

- Add applications with company, role, date, status, location, job link, notes.
- **Attach the resume PDF you used** — stored as a real file, re-downloadable anytime.
- Lifecycle stages: Applied → Online Assessment → Interview → Offer → Accepted / Rejected.
- **Follow-up reminders** — overdue ones surface in an alert banner.
- Live search, status filters, and animated stat counters.
- 🎉 Confetti celebration when a status becomes Offer or Accepted.
- Export everything to CSV.

## Tech stack

- **Backend:** Flask, SQLite (Python standard library)
- **Frontend:** HTML, CSS, vanilla JavaScript (no build step)
- **Animation:** CSS keyframes + IntersectionObserver + canvas-confetti

## Setup

```bash
pip install -r requirements.txt
python server.py
```

Then open **http://localhost:5000** in your browser.

## Project structure

```
application_tracker/
├── server.py              # Flask app: routes + REST API + DB
├── templates/index.html   # the single-page UI
├── static/css/styles.css  # premium animated styling
├── static/js/main.js       # front-end logic
├── requirements.txt
└── data/                  # created on first run (git-ignored)
    ├── tracker.db         # your applications
    └── resumes/           # the resume PDFs you attached
```

## Credits

Hero image: ["Open road leads to sunlit hills at sunrise"](https://unsplash.com/photos/open-road-leads-to-sunlit-hills-at-sunrise-JUDGhaboPE8)
by Tim Mossholder on [Unsplash](https://unsplash.com/) (free to use under the Unsplash License).

## Your data stays private

Everything runs on your machine and binds to `127.0.0.1` only — nothing is
uploaded anywhere. The `data/` folder (database + resume PDFs) is **git-ignored**,
so your applications and resumes are never committed to GitHub.
