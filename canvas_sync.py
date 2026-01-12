#!/usr/bin/env python3
"""
Canvas Assignments to CalDAV Tasks Sync
Fetches assignments from Canvas ICS feed and creates tasks in CalDAV
Also adds "no classes" events to the School calendar
"""

import sys
import requests

from config import load_config
from canvas import fetch_canvas_items
from caldav_client import connect_caldav
from sync import sync_to_caldav


def main(config_path: str = "config.toml"):
    """Main entry point."""
    print("=" * 70)
    print("🎓 Canvas to CalDAV Task Sync")
    print("=" * 70)

    try:
        config = load_config(config_path)

        assignments, no_class_events = fetch_canvas_items(config)

        if not assignments and not no_class_events:
            print("\n📭 No items found to sync")
            return

        password = config["caldav"].get("password", "")
        if not password:
            print("\n⚠️  No password set - skipping CalDAV sync (list-only mode)")
            return

        calendar = connect_caldav(config)
        sync_to_caldav(assignments, no_class_events, calendar)

        print("\n✨ Sync complete!")

    except requests.RequestException as e:
        print(f"\n❌ Network error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.toml"
    main(config_file)
