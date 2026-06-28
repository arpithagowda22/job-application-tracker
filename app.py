"""
app.py — Job Application Tracker
--------------------------------
A small Streamlit web app to track job applications and, crucially, to store
the exact resume file you used for each company. When a company calls back,
you can instantly download the matching resume version.

Data is stored locally:
    - data/tracker.db        : SQLite database of application records
    - data/resumes/          : the uploaded resume PDFs themselves

Run:  streamlit run app.py
"""

import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# --- Configuration -----------------------------------------------------------
DATA_DIR = Path("data")
RESUME_DIR = DATA_DIR / "resumes"          # where uploaded resume files live
DB_PATH = DATA_DIR / "tracker.db"          # SQLite database file

# The lifecycle stages an application can move through.
STATUSES = ["Applied", "Online Assessment", "Interview", "Offer", "Accepted", "Rejected"]

# Once an application reaches one of these stages, follow-up reminders no longer
# matter (the process is over), so we stop flagging them as "due".
TERMINAL_STATUSES = {"Accepted", "Rejected"}

# A color per status, used to make the dashboard easy to scan at a glance.
STATUS_COLORS = {
    "Applied": "#3b82f6",
    "Online Assessment": "#8b5cf6",
    "Interview": "#f59e0b",
    "Offer": "#10b981",
    "Accepted": "#059669",
    "Rejected": "#ef4444",
}


# --- Database layer ----------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection. check_same_thread=False keeps Streamlit happy."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_storage() -> None:
    """
    Make sure the data folders and the database table exist.
    Safe to call every run — it only creates things if missing.
    """
    DATA_DIR.mkdir(exist_ok=True)
    RESUME_DIR.mkdir(exist_ok=True)

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                company         TEXT NOT NULL,
                role            TEXT,
                date_applied    TEXT,
                status          TEXT,
                location        TEXT,
                job_link        TEXT,
                notes           TEXT,
                resume_filename TEXT,   -- original name, shown to the user
                resume_path     TEXT,   -- actual saved path on disk
                follow_up_date  TEXT,   -- optional date to chase a reply
                created_at      TEXT
            )
            """
        )
        conn.commit()
        _migrate_add_missing_columns(conn)


def _migrate_add_missing_columns(conn: sqlite3.Connection) -> None:
    """
    Add any newer columns to an older database created before they existed.
    This lets the app upgrade in place without losing your data.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(applications)")}
    if "follow_up_date" not in existing:
        conn.execute("ALTER TABLE applications ADD COLUMN follow_up_date TEXT")
        conn.commit()


def save_resume_file(uploaded_file) -> tuple[str, str]:
    """
    Save an uploaded resume to the resumes folder under a unique name so two
    companies can never overwrite each other's file.

    Returns (original_filename, saved_path_as_string).
    """
    # Prefix with a short unique id to avoid name collisions, keep the real name readable.
    unique_prefix = uuid.uuid4().hex[:8]
    safe_name = f"{unique_prefix}_{uploaded_file.name}"
    dest = RESUME_DIR / safe_name
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return uploaded_file.name, str(dest)


def add_application(data: dict) -> None:
    """Insert one application record into the database."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO applications
                (company, role, date_applied, status, location, job_link,
                 notes, resume_filename, resume_path, follow_up_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["company"], data["role"], data["date_applied"], data["status"],
                data["location"], data["job_link"], data["notes"],
                data["resume_filename"], data["resume_path"], data["follow_up_date"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def fetch_applications() -> pd.DataFrame:
    """Return all applications as a DataFrame, newest first."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM applications ORDER BY date_applied DESC, id DESC", conn
        )


def update_status(app_id: int, new_status: str) -> None:
    """Change the status of one application (e.g. Applied -> Interview)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id)
        )
        conn.commit()


def delete_application(app_id: int) -> None:
    """Delete an application and remove its stored resume file from disk."""
    with get_connection() as conn:
        # First look up the resume path so we can clean up the file too.
        row = conn.execute(
            "SELECT resume_path FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
        if row and row[0]:
            resume_file = Path(row[0])
            if resume_file.exists():
                resume_file.unlink()  # delete the orphaned PDF
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()


# --- UI helpers --------------------------------------------------------------
def status_badge(status: str) -> str:
    """Build a small colored HTML pill for a status label."""
    color = STATUS_COLORS.get(status, "#6b7280")
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.8rem;'>{status}</span>"
    )


def render_add_form() -> None:
    """Sidebar form for adding a new application with its resume."""
    st.sidebar.header("➕ Add application")

    with st.sidebar.form("add_form", clear_on_submit=True):
        company = st.text_input("Company *")
        role = st.text_input("Role / Position")
        date_applied = st.date_input("Date applied", value=date.today())
        status = st.selectbox("Status", STATUSES, index=0)
        location = st.text_input("Location")
        job_link = st.text_input("Job posting link")
        notes = st.text_area("Notes", placeholder="Referral, recruiter name, salary, etc.")
        resume = st.file_uploader("Resume used (PDF) *", type=["pdf"])

        # Optional follow-up reminder. The checkbox keeps the date optional —
        # only saved if the user actually wants to be reminded.
        set_follow_up = st.checkbox("Set a follow-up reminder")
        follow_up_date = st.date_input(
            "Follow up on", value=date.today(), disabled=not set_follow_up
        )

        submitted = st.form_submit_button("Save application")

    if submitted:
        # Validate the two required fields before saving.
        if not company.strip():
            st.sidebar.error("Company is required.")
            return
        if resume is None:
            st.sidebar.error("Please attach the resume you used.")
            return

        resume_filename, resume_path = save_resume_file(resume)
        add_application({
            "company": company.strip(),
            "role": role.strip(),
            "date_applied": date_applied.isoformat(),
            "status": status,
            "location": location.strip(),
            "job_link": job_link.strip(),
            "notes": notes.strip(),
            "resume_filename": resume_filename,
            "resume_path": resume_path,
            # Only store the follow-up date if the reminder checkbox was ticked.
            "follow_up_date": follow_up_date.isoformat() if set_follow_up else None,
        })
        st.sidebar.success(f"Saved application to {company}!")
        st.rerun()


def due_followups(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return applications whose follow-up date is today or earlier and that are
    still active (not already accepted/rejected) — i.e. the ones to chase now.
    """
    if df.empty or "follow_up_date" not in df.columns:
        return df.iloc[0:0]
    today = date.today().isoformat()
    mask = (
        df["follow_up_date"].notna()
        & (df["follow_up_date"] != "")
        & (df["follow_up_date"] <= today)            # string ISO dates compare correctly
        & (~df["status"].isin(TERMINAL_STATUSES))
    )
    return df[mask]


def render_metrics(df: pd.DataFrame) -> None:
    """Show a row of summary numbers at the top of the dashboard."""
    total = len(df)
    interviews = int((df["status"] == "Interview").sum()) if total else 0
    offers = int(df["status"].isin(["Offer", "Accepted"]).sum()) if total else 0
    due = len(due_followups(df))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total applications", total)
    c2.metric("Interviews", interviews)
    c3.metric("Offers", offers)
    c4.metric("Follow-ups due", due)


def render_followup_alerts(df: pd.DataFrame) -> None:
    """Show a warning banner listing applications that need chasing today."""
    due = due_followups(df)
    if due.empty:
        return
    st.warning(f"⏰ You have **{len(due)}** follow-up(s) due:")
    for _, row in due.iterrows():
        st.markdown(
            f"- **{row['company']}** ({row['role'] or 'role n/a'}) — "
            f"follow up since **{row['follow_up_date']}**, status: {row['status']}"
        )


def render_application_row(row: pd.Series) -> None:
    """Render a single application as an expandable card with actions."""
    title = f"{row['company']} — {row['role'] or 'Role n/a'}"
    with st.expander(title):
        # Header line: status badge + date applied.
        st.markdown(
            f"{status_badge(row['status'])} &nbsp; applied **{row['date_applied']}**",
            unsafe_allow_html=True,
        )

        if row["location"]:
            st.write(f"📍 {row['location']}")
        if row["job_link"]:
            st.write(f"🔗 [Job posting]({row['job_link']})")
        if row["notes"]:
            st.write(f"📝 {row['notes']}")

        # Show the follow-up date, flagged red if it's already due.
        follow_up = row.get("follow_up_date")
        if follow_up:
            is_due = follow_up <= date.today().isoformat() and row["status"] not in TERMINAL_STATUSES
            if is_due:
                st.markdown(f"⏰ **Follow-up due since {follow_up}**")
            else:
                st.write(f"⏰ Follow up on {follow_up}")

        # The whole point of the app: get back the exact resume used.
        resume_path = Path(row["resume_path"]) if row["resume_path"] else None
        if resume_path and resume_path.exists():
            with open(resume_path, "rb") as f:
                st.download_button(
                    "⬇️ Download the resume used",
                    data=f.read(),
                    file_name=row["resume_filename"],
                    mime="application/pdf",
                    key=f"dl_{row['id']}",
                )
        else:
            st.warning("Resume file missing on disk.")

        # Actions: change status or delete this application.
        col_status, col_delete = st.columns([3, 1])
        with col_status:
            new_status = st.selectbox(
                "Update status",
                STATUSES,
                index=STATUSES.index(row["status"]) if row["status"] in STATUSES else 0,
                key=f"status_{row['id']}",
            )
            if new_status != row["status"]:
                update_status(int(row["id"]), new_status)
                st.rerun()
        with col_delete:
            st.write("")  # spacer to align the button
            if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                delete_application(int(row["id"]))
                st.rerun()


# --- Main app ----------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Job Application Tracker", page_icon="📋", layout="wide")
    init_storage()

    st.title("📋 Job Application Tracker")
    st.caption("Track every application and the exact resume you used for each company.")

    render_add_form()

    df = fetch_applications()

    if df.empty:
        st.info("No applications yet. Use the sidebar on the left to add your first one. 👈")
        return

    render_metrics(df)
    render_followup_alerts(df)
    st.divider()

    # --- Filters: search by company and filter by status ---
    fcol1, fcol2 = st.columns([2, 2])
    with fcol1:
        search = st.text_input("🔍 Search company or role").strip().lower()
    with fcol2:
        status_filter = st.multiselect("Filter by status", STATUSES, default=[])

    filtered = df.copy()
    if search:
        mask = (
            filtered["company"].str.lower().str.contains(search, na=False)
            | filtered["role"].str.lower().str.contains(search, na=False)
        )
        filtered = filtered[mask]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    st.write(f"Showing **{len(filtered)}** of {len(df)} applications")

    # Render each application as a card.
    for _, row in filtered.iterrows():
        render_application_row(row)

    # --- Export: download the whole tracker as CSV (without the resume blobs) ---
    st.divider()
    export_cols = [
        "company", "role", "date_applied", "status", "location",
        "job_link", "notes", "resume_filename", "follow_up_date",
    ]
    csv = df[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export all as CSV", data=csv, file_name="job_applications.csv", mime="text/csv"
    )


if __name__ == "__main__":
    main()
