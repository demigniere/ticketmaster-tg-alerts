import requests
import json

# Ticketmaster API key
TM_API_KEY = 'AOB0wKnS5R6I2j5CbqGsgAGQgoGuDLzN'

# A set to store event IDs we've already processed to avoid duplicates
sent_event_ids = set()

# Function to load cities from a JSON file
def load_cities_from_json(filename, user_id):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            # Return the list of cities for the specific user ID
            return data.get(str(user_id), [])
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding the JSON file.")
        return []

# Function to fetch events from Ticketmaster API
def get_events(city):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        'apikey': TM_API_KEY,
        'city': city,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Return the list of events or empty list if no events
        return data.get('_embedded', {}).get('events', [])
    except requests.RequestException as e:
        print(f"Error fetching events for {city}: {e}")
        return []

# Function to print event details to the console
def print_event_details(city, events):
    new_events = [event for event in events if event['id'] not in sent_event_ids]

    if not new_events:
        print(f"No new events found in {city}.")
        return

    # Mark events as processed
    for event in new_events:
        sent_event_ids.add(event['id'])

    # Print event details
    print(f"--- Events in {city} ---")
    for event in new_events:
        name = event['name']
        date = event['dates']['start']['localDate']
        url = event['url']
        print(f"Event: {name}")
        print(f"Date: {date}")
        print(f"Get Tickets: {url}")
        print("-" * 50)

# Main function
def main():
    # Assume you have a user ID to fetch cities for
    user_id = 905884210  # Example user ID, replace with actual user ID

    # Load cities for this user from the JSON file
    cities = load_cities_from_json('cities.json', user_id)

    if not cities:
        print(f"No cities found for user {user_id}.")
        return

    for city in cities:
        print(f"Searching for events in {city}...")
        events = get_events(city)
        print_event_details(city, events)

if __name__ == '__main__':
    main()