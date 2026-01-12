import requests
from icalendar import Calendar
import datetime


# The fetch_calendar_data and parse_calendar_data functions remain the same
def fetch_calendar_data(url):
    """Fetches iCalendar data from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching calendar data from {url}: {e}")
        return None


def parse_calendar_data(ics_content):
    """Parses iCalendar content and returns a Calendar object."""
    try:
        return Calendar.from_ical(ics_content)
    except Exception as e:
        print(f"Error parsing iCalendar data: {e}")
        return None


def display_event_details_comprehensive(event):
    """
    Displays all available details for a single event, including parameters
    and less common properties.
    """
    print("\n--- Comprehensive Event Details ---")
    print(f"Event Type: {event.name}")  # Should be VEVENT

    # `event.items()` iterates through all properties attached to the VEVENT component
    for prop_name, prop_value in event.items():
        print(f"  Property Name: {prop_name}")

        # Handle the main value of the property
        if hasattr(
            prop_value, "dt"
        ):  # For DTSTART, DTEND, CREATED, LAST-MODIFIED, etc.
            dt_object = prop_value.dt
            if isinstance(dt_object, datetime.datetime):
                # Use 'seconds' for full detail in comprehensive view
                print(
                    f"    Value (Datetime): {dt_object.isoformat(timespec='seconds')}"
                )
            elif isinstance(dt_object, datetime.date):
                print(f"    Value (Date): {dt_object.isoformat()} (All Day)")
            else:
                print(f"    Value (Raw Date/Time Object): {str(dt_object)}")
        elif hasattr(
            prop_value, "to_ical"
        ):  # For things like URL, Organizer, RRULE, etc.
            # `to_ical()` returns bytes, so decode to string for display
            print(
                f"    Value (iCal Representation): {prop_value.to_ical().decode('utf-8')}"
            )
        else:  # For simple text properties (SUMMARY, DESCRIPTION, LOCATION, UID, STATUS)
            print(f"    Value (String/Raw): {str(prop_value)}")

        # Check for and display parameters associated with this property
        # Parameters are stored in the `.params` attribute of a Property object
        if hasattr(prop_value, "params") and prop_value.params:
            print("    Parameters:")
            for param_name, param_values in prop_value.params.items():
                # Parameters can sometimes be lists (e.g., CATEGORIES: A,B,C)
                if isinstance(param_values, list):
                    print(
                        f"      - {param_name}: {', '.join(str(v) for v in param_values)}"
                    )
                else:
                    print(f"      - {param_name}: {str(param_values)}")
        print("  ---")  # Separator for properties

    print("-----------------------------------\n")


def main():
    # Ensure this URL is correct for your specific Canvas calendar feed.
    calendar_url = "https://utahtech.instructure.com/feeds/calendars/user_fLZ4F8kSwFwArS85XptkSqtdQ5SsoSbN4CFqfl4R.ics"

    ics_content = fetch_calendar_data(calendar_url)
    if not ics_content:
        return

    cal = parse_calendar_data(ics_content)
    if not cal:
        return

    # Filter for VEVENT components. cal.walk() iterates through all components.
    events = [component for component in cal.walk("vevent")]

    if not events:
        print("No events found in the calendar.")
        return

    print(f"Found {len(events)} events.")
    print("---------------------\n")
    for i, event in enumerate(events):
        summary = str(
            event.get("summary", "No Summary")
        ).strip()  # Use strip to clean up whitespace

        # Safely get and format the start time for the listing
        start_time_ical = event.get("dtstart")
        start_str = "N/A"  # Default value if no dtstart or error

        if start_time_ical and hasattr(start_time_ical, "dt"):
            dt_object = start_time_ical.dt
            if isinstance(dt_object, datetime.datetime):
                start_str = dt_object.isoformat(timespec="minutes")
            elif isinstance(dt_object, datetime.date):
                start_str = dt_object.isoformat() + " (All Day)"
            # If it's some other unexpected type, start_str remains 'N/A'

        print(f"{i+1}. {summary} (Starts: {start_str})")
    print("\n---------------------\n")

    while True:
        try:
            choice = (
                input(
                    f"Enter the number of the event you want to view (1-{len(events)}), or 'q' to quit: "
                )
                .strip()
                .lower()
            )

            if choice == "q":
                break

            event_index = int(choice) - 1  # Convert to 0-based index
            if 0 <= event_index < len(events):
                # Call the new comprehensive display function
                display_event_details_comprehensive(events[event_index])

                # Ask if they want to view another event or quit
                cont = input("View another event? (y/n): ").strip().lower()
                if cont != "y":
                    break
            else:
                print(
                    f"Invalid event number. Please enter a number between 1 and {len(events)}."
                )
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")


if __name__ == "__main__":
    main()
