"""Configuration loading and management."""

import tomllib
from pathlib import Path
from datetime import datetime, date


def load_config(config_path: str = "config.toml") -> dict:
    """Load configuration from TOML file."""
    path = Path(config_path)

    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("   Creating default config.toml...")
        create_default_config(path)
        print(f"   Please edit {config_path} and run again.")
        exit(1)

    with open(path, "rb") as f:
        return tomllib.load(f)


def create_default_config(path: Path):
    """Create a default configuration file."""
    default_config = """# Canvas to CalDAV Sync Configuration

[canvas]
# Your Canvas ICS feed URL
feed_url = "https://example.instructure.com/feeds/calendars/user_XXXXX.ics"

[caldav]
# CalDAV server settings
url = "https://your-caldav-server.com/caldav/"
username = "your_username"
password = "your_app_token"  # or it may be your password

# Target calendar/task list name
calendar_name = "School"

[sync]
# Date filter - only sync items on or before this date (inclusive)
# Set to empty string "" to sync everything
# Format: YYYY-MM-DD
end_date = "2026-05-08"

# Keywords to identify "no class" events (case-insensitive)
# Events with these words in the summary become calendar events
no_class_keywords = ["no classes", "no school", "holiday", "break"]

# How class assignments, labs, quizzes, and exams are identified and tagged:
#
# 1. Automatic Course Tagging:
#    If an item's summary contains a pattern like "[COURSE-ID-SECTION Course Name]"
#    (e.g., "[HIST-1700-07 American History]"), it will be automatically
#    categorized as an assignment/task and tagged with the "COURSE-ID" (e.g., "HIST-1700").
#    This takes precedence over the keywords below for initial categorization,
#    unless it's a "no class" event.
#
# 2. Automatic Assignment Type Tagging:
#    For items identified as assignments, an additional tag will be applied
#    based on keywords in their summary (e.g., "Practical", "Exam", "Lab").
#    If no specific type keyword is found, it will default to "Assignment".
#    You can customize these keywords in the `canvas.py` file under `ASSIGNMENT_TYPE_KEYWORDS`.

# Keywords in UID to identify additional assignments (case-insensitive)
# Events with these words in the UID become tasks. (Lower precedence than course ID pattern).
assignment_keywords = ["assignment"]

# Keywords in summary to identify additional assignments (case-insensitive)
# Events with these words in the summary become tasks. (Lowest precedence).
assignment_summary_keywords = [
    "assignment",
    "lab",
    "quiz",
    "exam",
    "slides",
    "discussion",
    "project",
    "homework",
    "paper",
    "report",
    "case study",
    "presentation",
    "test",
    "review",
    "final"
]
"""
    with open(path, "w") as f:
        f.write(default_config)


def parse_end_date(date_str: str) -> date | None:
    """Parse end date from config string."""
    if not date_str or date_str.strip() == "":
        return None

    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        print(f"⚠️  Invalid date format: {date_str}")
        print("   Expected format: YYYY-MM-DD")
        return None
