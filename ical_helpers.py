"""iCalendar component creation and manipulation."""

import hashlib
from datetime import datetime, timezone
from icalendar import Todo, Event


def compute_item_hash(item: dict) -> str:
    """Compute a hash of item content to detect changes."""
    content = f"{item.get('summary', '')}"
    content += f"|{item.get('description', '')}"
    content += f"|{item.get('url', '')}"
    content += f"|{item.get('location', '')}"

    dtstart = item.get("dtstart")
    if dtstart:
        content += f"|start:{dtstart.dt}"
    dtend = item.get("dtend")
    if dtend:
        content += f"|end:{dtend.dt}"

    # Include course_id and type_tag in hash calculation to detect tag changes
    if item.get("course_id"):
        content += f"|course_id:{item['course_id']}"
    if item.get("type_tag"):  # NEW: Include type_tag in hash
        content += f"|type_tag:{item['type_tag']}"

    return hashlib.md5(content.encode()).hexdigest()[:16]


def create_uid(canvas_uid: str, prefix: str) -> str:
    """Create a unique UID based on Canvas UID."""
    return f"canvas-{prefix}-{canvas_uid}"


def assignment_to_vtodo(assignment: dict, content_hash: str) -> tuple[Todo, str]:
    """Convert a Canvas assignment to a VTODO component."""
    todo = Todo()

    task_uid = create_uid(assignment["uid"], "task")
    todo.add("uid", task_uid)
    todo.add("summary", assignment["summary"])

    due_date = assignment.get("dtend") or assignment.get("dtstart")
    if due_date:
        todo.add("due", due_date.dt)

    description_parts = []
    if assignment["description"]:
        description_parts.append(assignment["description"])
    if assignment["url"]:
        description_parts.append(f"\nCanvas: {assignment['url']}")
    if description_parts:
        todo.add("description", "\n".join(description_parts))

    if assignment["url"]:
        todo.add("url", assignment["url"])

    now = datetime.now(timezone.utc)
    todo.add("dtstamp", now)
    todo.add("created", now)
    todo.add("last-modified", now)
    todo.add("status", "NEEDS-ACTION")
    todo.add("priority", 5)
    todo.add("x-canvas-hash", content_hash)

    # Add course_id and type_tag as CATEGORIES property
    categories = []
    if assignment.get("course_id"):
        categories.append(assignment["course_id"])
    if assignment.get("type_tag"):  # NEW: Add type_tag to categories
        categories.append(assignment["type_tag"])
    if categories:
        todo.add("categories", categories)

    return todo, task_uid


def update_vtodo(existing_component, assignment: dict, content_hash: str) -> Todo:
    """Update an existing VTODO component with new data, preserving status."""
    todo = Todo()

    task_uid = create_uid(assignment["uid"], "task")
    todo.add("uid", task_uid)
    todo.add("summary", assignment["summary"])

    due_date = assignment.get("dtend") or assignment.get("dtstart")
    if due_date:
        todo.add("due", due_date.dt)

    description_parts = []
    if assignment["description"]:
        description_parts.append(assignment["description"])
    if assignment["url"]:
        description_parts.append(f"\nCanvas: {assignment['url']}")
    if description_parts:
        todo.add("description", "\n".join(description_parts))

    if assignment["url"]:
        todo.add("url", assignment["url"])

    now = datetime.now(timezone.utc)
    todo.add("dtstamp", now)

    original_created = existing_component.get("created")
    if original_created:
        todo.add("created", original_created.dt)
    else:
        todo.add("created", now)

    todo.add("last-modified", now)

    original_status = str(existing_component.get("status", "NEEDS-ACTION"))
    todo.add("status", original_status)

    original_percent = existing_component.get("percent-complete")
    if original_percent:
        todo.add("percent-complete", original_percent)

    original_completed = existing_component.get("completed")
    if original_completed:
        todo.add("completed", original_completed.dt)

    todo.add("priority", 5)
    todo.add("x-canvas-hash", content_hash)

    # Add course_id and type_tag as CATEGORIES property
    categories = []
    if assignment.get("course_id"):
        categories.append(assignment["course_id"])
    if assignment.get("type_tag"):  # NEW: Add type_tag to categories
        categories.append(assignment["type_tag"])
    if categories:
        todo.add("categories", categories)

    return todo


def no_class_to_vevent(item: dict, content_hash: str) -> tuple[Event, str]:
    """Convert a no-class day to a VEVENT component."""
    event = Event()

    event_uid = create_uid(item["uid"], "event")
    event.add("uid", event_uid)
    event.add("summary", item["summary"])

    if item.get("dtstart"):
        event.add("dtstart", item["dtstart"].dt)
    if item.get("dtend"):
        event.add("dtend", item["dtend"].dt)

    if item["description"]:
        event.add("description", item["description"])

    if item["url"]:
        event.add("url", item["url"])

    now = datetime.now(timezone.utc)
    event.add("dtstamp", now)
    event.add("created", now)
    event.add("last-modified", now)
    event.add("x-canvas-hash", content_hash)

    # Add course_id as a CATEGORIES property for events as well if desired
    # (type_tag is generally not relevant for 'no class' events, but course_id might be in summary)
    categories = []
    if item.get("course_id"):
        categories.append(item["course_id"])
    if categories:
        event.add("categories", categories)

    return event, event_uid


def update_vevent(existing_component, item: dict, content_hash: str) -> Event:
    """Update an existing VEVENT component with new data."""
    event = Event()

    event_uid = create_uid(item["uid"], "event")
    event.add("uid", event_uid)
    event.add("summary", item["summary"])

    if item.get("dtstart"):
        event.add("dtstart", item["dtstart"].dt)
    if item.get("dtend"):
        event.add("dtend", item["dtend"].dt)

    if item["description"]:
        event.add("description", item["description"])

    if item["url"]:
        event.add("url", item["url"])

    now = datetime.now(timezone.utc)
    event.add("dtstamp", now)

    original_created = existing_component.get("created")
    if original_created:
        event.add("created", original_created.dt)
    else:
        event.add("created", now)

    event.add("last-modified", now)
    event.add("x-canvas-hash", content_hash)

    # Add course_id as a CATEGORIES property for events as well if desired
    categories = []
    if item.get("course_id"):
        categories.append(item["course_id"])
    if categories:
        event.add("categories", categories)

    return event
