"""Canvas ICS feed fetching and parsing."""

import requests
from icalendar import Calendar
from datetime import datetime, date
import re

from config import parse_end_date


# Define keywords for specific assignment types
ASSIGNMENT_TYPE_KEYWORDS = {
    "Practical": ["practical"],
    "Exam": ["exam", "midterm", "final", "test"],
    "Essay": ["essay", "paper", "report"],
    "Lab": ["lab"],
    "Presentation": ["presentation", "slides"],  # Added "slides" here
    "Discussion": ["discussion"],
    "Project": ["project"],
    "Quiz": ["quiz"],
    # Add more specific keywords here if needed, in desired priority order
    # Keywords are checked in order defined, so put more specific ones first
}
DEFAULT_ASSIGNMENT_TYPE_TAG = "Assignment"


def get_item_date(item: dict) -> date | None:
    """Extract date from an item, handling both date and datetime objects."""
    dtstart = item.get("dtstart")
    if not dtstart:
        return None

    dt = dtstart.dt

    if isinstance(dt, datetime):
        return dt.date()
    elif isinstance(dt, date):
        return dt

    return None


def is_within_date_range(item: dict, end_date: date | None) -> bool:
    """Check if item is within the configured date range."""
    if end_date is None:
        return True

    item_date = get_item_date(item)

    if item_date is None:
        # Items without a specific date (e.g., all-day events without DTSTART/DTEND)
        # are generally included, unless explicitly filtered otherwise.
        # For Canvas, DTSTART is almost always present.
        return True

    return item_date <= end_date


def matches_keywords(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    if not keywords:
        return False
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def extract_course_id_from_summary(summary: str) -> str | None:
    """Extracts a course ID like 'HIST-1700' from a summary string."""
    # Matches patterns like "[COURSE-ID-SECTION Course Name]" or "[COURSE-ID Course Name]"
    # e.g., "[HIST-1700-07 American History]" -> "HIST-1700"
    # e.g., "[IT-3150 Windows Servers]" -> "IT-3150"
    match = re.search(r"\[([A-Z0-9-]+)(?:-\d{2})? [^\]]+\]", summary)
    if match:
        return match.group(1)  # The first captured group is the course ID
    return None


def get_assignment_type_tag(summary: str) -> str:
    """Determines the assignment type tag based on keywords in the summary."""
    summary_lower = summary.lower()
    for tag, keywords in ASSIGNMENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            # Use regex for whole word matching to avoid false positives (e.g., "lab" not matching "label")
            if re.search(r"\b" + re.escape(keyword) + r"\b", summary_lower):
                return tag
    return DEFAULT_ASSIGNMENT_TYPE_TAG


def fetch_canvas_items(config: dict) -> tuple[list, list]:
    """Download and parse Canvas ICS feed, categorizing items."""
    print("📥 Downloading Canvas Feed...")

    feed_url = config["canvas"]["feed_url"]
    end_date = parse_end_date(config["sync"].get("end_date", ""))

    # Get keywords from config with defaults
    no_class_keywords = config["sync"].get(
        "no_class_keywords", ["no classes", "no school", "holiday", "break"]
    )
    assignment_uid_keywords = config["sync"].get("assignment_keywords", ["assignment"])
    assignment_summary_keywords = config["sync"].get("assignment_summary_keywords", [])

    if end_date:
        print(f"📅 Filtering items until: {end_date.strftime('%B %d, %Y')}")
    else:
        print("📅 No date filter - syncing all items")

    print(f"🔍 No-class keywords: {no_class_keywords}")
    print(f"🔍 Assignment UID keywords: {assignment_uid_keywords}")
    print(f"🔍 Assignment summary keywords: {assignment_summary_keywords}")

    response = requests.get(feed_url)
    response.raise_for_status()

    cal = Calendar.from_ical(response.content)
    assignments = []
    no_class_events = []
    skipped = []
    filtered_out = []

    for component in cal.walk():
        if component.name == "VEVENT":
            summary = str(component.get("SUMMARY", ""))
            uid = str(component.get("UID", ""))
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")

            item_info = {
                "uid": uid,
                "summary": summary,
                "dtstart": dtstart,
                "dtend": dtend,
                "description": str(component.get("DESCRIPTION", "")),
                "url": str(component.get("URL", "")),
                "location": str(component.get("LOCATION", "")),
            }

            # Extract course ID and add to item_info
            course_id = extract_course_id_from_summary(summary)
            if course_id:
                item_info["course_id"] = course_id

            # Check date range first
            if not is_within_date_range(item_info, end_date):
                filtered_out.append(item_info)
                continue

            # Check for "no classes" events (highest priority)
            if matches_keywords(summary, no_class_keywords):
                no_class_events.append(item_info)
            # If it has a course ID and isn't a "no classes" event, it's an assignment
            elif item_info.get("course_id"):
                assignments.append(item_info)
            # Otherwise, check for assignments using keywords
            elif matches_keywords(uid, assignment_uid_keywords) or matches_keywords(
                summary, assignment_summary_keywords
            ):
                assignments.append(item_info)
            # Everything else gets skipped
            else:
                skipped.append(item_info)

            # --- New: Determine assignment type tag for items going into assignments ---
            if item_info in assignments:
                item_info["type_tag"] = get_assignment_type_tag(summary)

    # Print assignments
    print(f"\n{'='*70}")
    print(f"📚 ASSIGNMENTS → Tasks ({len(assignments)} found)")
    print(f"{'='*70}")
    for item in assignments:
        due = item.get("dtstart")
        due_str = str(due.dt) if due else "No date"
        tags_str = ""
        if item.get("course_id"):
            tags_str += f" [{item['course_id']}]"
        if item.get("type_tag"):
            tags_str += f" [{item['type_tag']}]"

        print(f"   📝 {item['summary'][:50]}{tags_str}")
        print(f"      Due: {due_str}")
        print(f"      UID: {item['uid']}")
        print()

    # Print no class events
    print(f"\n{'='*70}")
    print(f"🏖️  NO CLASS DAYS → Calendar Events ({len(no_class_events)} found)")
    print(f"{'='*70}")
    for item in no_class_events:
        item_date = item.get("dtstart")
        date_str = str(item_date.dt) if item_date else "No date"
        tags_str = ""
        if item.get("course_id"):
            tags_str += f" [{item['course_id']}]"  # No-class events can still have course IDs in summary
        print(f"   🎉 {item['summary'][:50]}{tags_str}")
        print(f"      Date: {date_str}")
        print(f"      UID: {item['uid']}")
        print()

    # Print skipped
    print(f"\n{'='*70}")
    print(f"⏭️  SKIPPED ({len(skipped)} found)")
    print(f"{'='*70}")
    for item in skipped:
        item_date = item.get("dtstart")
        date_str = str(item_date.dt) if item_date else "No date"
        tags_str = ""
        if item.get("course_id"):
            tags_str += f" [{item['course_id']}]"
        print(f"   ❌ {item['summary'][:50]}{tags_str}")
        print(f"      Date: {date_str}")
        print(f"      UID: {item['uid']}")
        print()

    # Print filtered out (past end date)
    if filtered_out:
        end_date = parse_end_date(config["sync"].get("end_date", ""))
        print(f"\n{'='*70}")
        print(f"📆 FILTERED OUT - After {end_date} ({len(filtered_out)} found)")
        print(f"{'='*70}")
        for item in filtered_out:
            item_date = item.get("dtstart")
            date_str = str(item_date.dt) if item_date else "No date"
            tags_str = ""
            if item.get("course_id"):
                tags_str += f" [{item['course_id']}]"
            print(f"   🚫 {item['summary'][:50]}{tags_str}")
            print(f"      Date: {date_str}")
            print()

    return assignments, no_class_events
