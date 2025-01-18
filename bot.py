import asyncio
import json
import os
import requests
import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TM_API_KEY = os.getenv("TM_API_KEY")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# File paths
CITIES_FILE = 'user_cities.json'
SENT_EVENTS_FILE = 'sent_events.json'

# Load and save JSON helpers
def load_json(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize data
user_cities = load_json(CITIES_FILE)
sent_events = load_json(SENT_EVENTS_FILE)

def save_cities():
    save_json(user_cities, CITIES_FILE)

# Main menu keyboard
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Manual check")],
        [KeyboardButton(text="City management")],
        [KeyboardButton(text="Profile")],
        [KeyboardButton(text="Toggle hourly updates")]
    ],
    resize_keyboard=True
)

# User states for input handling
user_states = {}

# Helper function to fetch events from Ticketmaster API
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
        return data.get('_embedded', {}).get('events', [])
    except requests.RequestException as e:
        print(f"Error fetching events for {city}: {e}")
        return []

# Function to send new events to users
async def send_events_to_user(user_id, city, events):
    global sent_events
    new_events = []
    for event in events:
        event_id = event['id']
        if event_id not in sent_events.get(str(user_id), []):
            new_events.append(event)
            sent_events.setdefault(str(user_id), []).append(event_id)
            save_json(sent_events, SENT_EVENTS_FILE)

    if new_events:
        for event in new_events:
            event_message = (
                f"--- Events in {city} ---\n\n"
                f"Event: {event['name']}\n"
                f"Date: {event['dates']['start']['localDate']}\n"
                f"Get Tickets: {event['url']}\n"
                f"{'-' * 50}\n"
            )
            await bot.send_message(user_id, event_message)
            await asyncio.sleep(0.5)  # Avoid flooding
    else:
        await bot.send_message(user_id, f"No new events found in {city}.")

# Hourly event checking loop
async def hourly_event_check():
    while True:
        print(f"Running hourly check at {datetime.datetime.now()}...")
        for user_id, user_data in user_cities.items():
            if user_data.get("auto_updates", True):
                for city in user_data.get("cities", []):
                    events = get_events(city)
                    await send_events_to_user(user_id, city, events)
        await asyncio.sleep(3600)

# Command Handlers
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in user_cities:
        user_cities[user_id] = {"auto_updates": True, "cities": []}
        save_cities()

    await message.reply(
        "Welcome! I will update you with new events automatically every hour. "
        "You can also check for all events manually (don't use this too often).",
        reply_markup=main_menu
    )

@dp.message(F.text == "Toggle hourly updates")
async def toggle_auto_updates(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = user_cities.setdefault(user_id, {"auto_updates": True, "cities": []})

    current_status = user_data["auto_updates"]
    user_data["auto_updates"] = not current_status
    save_cities()

    status_text = "enabled" if not current_status else "disabled"
    await message.reply(f"Automatic event updates have been {status_text}.")

@dp.message(F.text == "Manual check")
async def manual_event_check(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = user_cities.get(user_id, {"auto_updates": True, "cities": []})

    for city in user_data.get("cities", []):
        events = get_events(city)
        if events:
            await send_events_to_user(user_id, city, events)
        else:
            await message.reply(f"No events found for {city}.")

@dp.message(F.text == "City management")
async def city_management(message: types.Message):
    city_management_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="View cities")],
            [KeyboardButton(text="Add city")],
            [KeyboardButton(text="Remove city")],
            [KeyboardButton(text="Back to Main Menu")]
        ],
        resize_keyboard=True
    )
    await message.reply("Choose a city management option:", reply_markup=city_management_menu)

@dp.message(F.text == "Back to Main Menu")
async def back_to_main_menu(message: types.Message):
    await message.reply("Returning to the main menu...", reply_markup=main_menu)

@dp.message(F.text == "View cities")
async def view_cities(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = user_cities.get(user_id, {"auto_updates": True, "cities": []})
    cities = user_data["cities"]

    if not cities:
        await message.reply("No cities in your list yet.")
    else:
        await message.reply("Your cities:\n" + "\n".join(cities))

@dp.message(F.text == "Add city")
async def start_add_city(message: types.Message):
    user_id = str(message.from_user.id)
    user_states[user_id] = 'adding_city'
    await message.reply("Please enter the name of the city to add:")

@dp.message(F.text == "Remove city")
async def start_remove_city(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = user_cities.get(user_id, {"auto_updates": True, "cities": []})
    cities = user_data.get("cities", [])  # Use .get() with default value

    if not cities:
        await message.reply("Your city list is empty.", reply_markup=main_menu)
        return

    builder = InlineKeyboardBuilder()
    # Add a unique identifier to ensure unique callback data
    for city in cities:
        # Ensure city name is URL-safe by replacing spaces with underscores
        safe_city = city.replace(" ", "_")
        builder.button(
            text=city,
            callback_data=f"remove_{safe_city}"
        )
    builder.adjust(1)

    await message.reply(
        "Select a city to remove:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("remove_"))
async def handle_callback(callback: types.CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        # Convert back from URL-safe format
        city = callback.data.split("remove_", 1)[1].replace("_", " ")

        if user_id not in user_cities:
            await callback.answer("User data not found.", show_alert=True)
            return

        user_data = user_cities[user_id]
        if "cities" not in user_data:
            user_data["cities"] = []

        if city in user_data["cities"]:
            user_data["cities"].remove(city)
            save_cities()  # Save changes immediately
            
            await callback.answer(f"Removed {city}", show_alert=True)
            
            if user_data["cities"]:
                # Create new keyboard with remaining cities
                builder = InlineKeyboardBuilder()
                for remaining_city in user_data["cities"]:
                    safe_city = remaining_city.replace(" ", "_")
                    builder.button(
                        text=remaining_city,
                        callback_data=f"remove_{safe_city}"
                    )
                builder.adjust(1)
                
                await callback.message.edit_text(
                    "Select another city to remove:",
                    reply_markup=builder.as_markup()
                )
            else:
                await callback.message.edit_text(
                    "Your city list is now empty.",
                    reply_markup=main_menu
                )
        else:
            await callback.answer(f"{city} is not in your list.", show_alert=True)
            
    except Exception as e:
        print(f"Error in callback handler: {e}")
        await callback.answer("An error occurred while removing the city.", show_alert=True)
        return

@dp.message(F.text == "Profile")
async def show_profile(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = user_cities.get(user_id, {"auto_updates": True, "cities": []})
    auto_updates = "enabled" if user_data.get("auto_updates", True) else "disabled"
    username = message.from_user.username or "Not set"
    await message.reply(
        f"Your profile:\n\n"
        f"Username: @{username}\n"
        f"User ID: {user_id}\n"
        f"Automatic updates: {auto_updates}\n"

    )

@dp.message(lambda message: user_states.get(str(message.from_user.id)) == 'adding_city')
async def add_city(message: types.Message):
    user_id = str(message.from_user.id)
    city = message.text.strip()
    user_data = user_cities.setdefault(user_id, {"auto_updates": True, "cities": []})
    cities = user_data["cities"]

    if city in cities:
        await message.reply(f"{city} is already in your list.")
    else:
        cities.append(city)
        save_cities()
        await message.reply(f"{city} has been added to your list.")

    user_states[user_id] = None

# Main function
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(hourly_event_check())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
