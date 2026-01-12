"""Sync logic between Canvas and CalDAV."""

from icalendar import Calendar

from caldav_client import get_existing_items
from ical_helpers import (
    compute_item_hash,
    create_uid,
    assignment_to_vtodo,
    update_vtodo,
    no_class_to_vevent,
    update_vevent,
)


def detect_changes(existing_component, new_item: dict, item_type: str) -> list[str]:
    """Detect what changed between existing and new item."""
    changes = []

    # Check summary
    old_summary = str(existing_component.get("summary", ""))
    new_summary = new_item.get("summary", "")
    if old_summary != new_summary:
        changes.append(f"Title: '{old_summary[:30]}' → '{new_summary[:30]}'")

    # Check description
    old_desc = str(existing_component.get("description", ""))
    new_desc = new_item.get("description", "")
    if new_item.get("url"):
        new_desc_full = (
            new_desc + f"\nCanvas: {new_item['url']}"
            if new_desc
            else f"\nCanvas: {new_item['url']}"
        )
    else:
        new_desc_full = new_desc
    if old_desc.strip() != new_desc_full.strip():
        old_preview = old_desc[:40].replace("\n", " ") if old_desc else "(empty)"
        new_preview = new_desc[:40].replace("\n", " ") if new_desc else "(empty)"
        changes.append(f"Description: '{old_preview}...' → '{new_preview}...'")

    # Check URL
    old_url = str(existing_component.get("url", ""))
    new_url = new_item.get("url", "")
    if old_url != new_url:
        changes.append(f"URL changed")

    # Check dates based on item type
    if item_type == "task":
        old_due = existing_component.get("due")
        new_due = new_item.get("dtend") or new_item.get("dtstart")
        old_due_str = str(old_due.dt) if old_due else "None"
        new_due_str = str(new_due.dt) if new_due else "None"
        if old_due_str != new_due_str:
            changes.append(f"Due: {old_due_str} → {new_due_str}")
    else:
        old_start = existing_component.get("dtstart")
        new_start = new_item.get("dtstart")
        old_start_str = str(old_start.dt) if old_start else "None"
        new_start_str = str(new_start.dt) if new_start else "None"
        if old_start_str != new_start_str:
            changes.append(f"Start: {old_start_str} → {new_start_str}")

        old_end = existing_component.get("dtend")
        new_end = new_item.get("dtend")
        old_end_str = str(old_end.dt) if old_end else "None"
        new_end_str = str(new_end.dt) if new_end else "None"
        if old_end_str != new_end_str:
            changes.append(f"End: {old_end_str} → {new_end_str}")

    # Check location (for events)
    old_location = str(existing_component.get("location", ""))
    new_location = new_item.get("location", "")
    if old_location != new_location:
        changes.append(f"Location: '{old_location}' → '{new_location}'")

    return changes


def sync_to_caldav(assignments: list, no_class_events: list, calendar):
    """Sync Canvas items to CalDAV."""
    print(f"\n🔄 Syncing to CalDAV...")

    existing_todos, existing_events = get_existing_items(calendar)
    print(
        f"   Found {len(existing_todos)} existing tasks, {len(existing_events)} existing events"
    )

    tasks_added = 0
    tasks_updated = 0
    tasks_unchanged = 0
    events_added = 0
    events_updated = 0
    events_unchanged = 0

    updated_items = []  # Track what was updated and why

    # Sync assignments as tasks
    print(f"\n   📚 Syncing assignments as tasks...")
    for assignment in assignments:
        task_uid = create_uid(assignment["uid"], "task")
        content_hash = compute_item_hash(assignment)

        if task_uid in existing_todos:
            existing = existing_todos[task_uid]

            if existing["hash"] == content_hash:
                print(f"      ⏭️  Unchanged: {assignment['summary'][:40]}")
                tasks_unchanged += 1
                continue

            changes = detect_changes(existing["component"], assignment, "task")
            print(f"      🔄 Updating: {assignment['summary'][:40]}")

            updated_items.append(
                {"type": "Task", "name": assignment["summary"], "changes": changes}
            )

            updated_todo = update_vtodo(existing["component"], assignment, content_hash)

            cal = Calendar()
            cal.add("prodid", "-//Canvas Task Sync//EN")
            cal.add("version", "2.0")
            cal.add_component(updated_todo)

            try:
                existing["object"].delete()
                calendar.save_todo(cal.to_ical().decode("utf-8"))
                tasks_updated += 1
            except Exception as e:
                print(f"      ❌ Update failed: {assignment['summary'][:40]} - {e}")
            continue

        todo, _ = assignment_to_vtodo(assignment, content_hash)

        cal = Calendar()
        cal.add("prodid", "-//Canvas Task Sync//EN")
        cal.add("version", "2.0")
        cal.add_component(todo)

        try:
            calendar.save_todo(cal.to_ical().decode("utf-8"))
            print(f"      ✅ Added: {assignment['summary'][:40]}")
            tasks_added += 1
        except Exception as e:
            print(f"      ❌ Failed: {assignment['summary'][:40]} - {e}")

    # Sync no-class days as events
    print(f"\n   🏖️  Syncing no-class days as events...")
    for item in no_class_events:
        event_uid = create_uid(item["uid"], "event")
        content_hash = compute_item_hash(item)

        if event_uid in existing_events:
            existing = existing_events[event_uid]

            if existing["hash"] == content_hash:
                print(f"      ⏭️  Unchanged: {item['summary'][:40]}")
                events_unchanged += 1
                continue

            changes = detect_changes(existing["component"], item, "event")
            print(f"      🔄 Updating: {item['summary'][:40]}")

            updated_items.append(
                {"type": "Event", "name": item["summary"], "changes": changes}
            )

            updated_event = update_vevent(existing["component"], item, content_hash)

            cal = Calendar()
            cal.add("prodid", "-//Canvas Task Sync//EN")
            cal.add("version", "2.0")
            cal.add_component(updated_event)

            try:
                existing["object"].delete()
                calendar.save_event(cal.to_ical().decode("utf-8"))
                events_updated += 1
            except Exception as e:
                print(f"      ❌ Update failed: {item['summary'][:40]} - {e}")
            continue

        event, _ = no_class_to_vevent(item, content_hash)

        cal = Calendar()
        cal.add("prodid", "-//Canvas Task Sync//EN")
        cal.add("version", "2.0")
        cal.add_component(event)

        try:
            calendar.save_event(cal.to_ical().decode("utf-8"))
            print(f"      ✅ Added: {item['summary'][:40]}")
            events_added += 1
        except Exception as e:
            print(f"      ❌ Failed: {item['summary'][:40]} - {e}")

    # Print detailed changes section
    if updated_items:
        print(f"\n{'='*70}")
        print(f"📝 DETAILED CHANGES ({len(updated_items)} items updated)")
        print(f"{'='*70}")
        for item in updated_items:
            print(f"\n   🔄 [{item['type']}] {item['name'][:50]}")
            if item["changes"]:
                for change in item["changes"]:
                    print(f"      • {change}")
            else:
                print(f"      • (metadata change only)")

    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(
        f"   Tasks:  {tasks_added} added, {tasks_updated} updated, {tasks_unchanged} unchanged"
    )
    print(
        f"   Events: {events_added} added, {events_updated} updated, {events_unchanged} unchanged"
    )
