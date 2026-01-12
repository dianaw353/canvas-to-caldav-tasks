"""CalDAV connection and operations."""

import caldav
from icalendar import Calendar


def connect_caldav(config: dict):
    """Connect to CalDAV server and find the target calendar."""
    print(f"\n🔗 Connecting to CalDAV server...")

    caldav_config = config["caldav"]

    client = caldav.DAVClient(
        url=caldav_config["url"],
        username=caldav_config["username"],
        password=caldav_config["password"],
    )

    principal = client.principal()
    calendars = principal.calendars()

    target_calendar = None
    target_name = caldav_config["calendar_name"]

    print(f"\n📋 Available calendars:")

    for cal in calendars:
        cal_name = cal.name
        print(f"   - {cal_name}")
        if cal_name == target_name:
            target_calendar = cal

    if not target_calendar:
        print(f"\n⚠️  Calendar '{target_name}' not found!")
        print("Creating new calendar...")
        target_calendar = principal.make_calendar(name=target_name)

    print(f"\n✅ Using calendar: {target_name}")
    return target_calendar


def get_existing_items(calendar) -> tuple[dict, dict]:
    """Get existing tasks and events with their UIDs, hashes, and objects."""
    existing_todos = {}
    existing_events = {}

    # Get existing todos
    try:
        todos = calendar.todos(include_completed=True)
        for todo in todos:
            try:
                ical = Calendar.from_ical(todo.data)
                for component in ical.walk():
                    if component.name == "VTODO":
                        uid = str(component.get("UID", ""))
                        if uid:
                            stored_hash = str(component.get("X-CANVAS-HASH", ""))
                            existing_todos[uid] = {
                                "hash": stored_hash,
                                "object": todo,
                                "component": component,
                            }
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️  Could not fetch existing tasks: {e}")

    # Get existing events
    try:
        events = calendar.events()
        for event in events:
            try:
                ical = Calendar.from_ical(event.data)
                for component in ical.walk():
                    if component.name == "VEVENT":
                        uid = str(component.get("UID", ""))
                        if uid:
                            stored_hash = str(component.get("X-CANVAS-HASH", ""))
                            existing_events[uid] = {
                                "hash": stored_hash,
                                "object": event,
                                "component": component,
                            }
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️  Could not fetch existing events: {e}")

    return existing_todos, existing_events
