import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# Replace with your actual Telegram bot token
BOT_TOKEN = '8178877597:AAE96gAegbosNqMYZm669rcmkK1aJjlPgq0'

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# File path to store user cities
CITIES_FILE = 'user_cities.json'

def load_cities():
    try:
        with open(CITIES_FILE, 'r') as f:
            cities_data = json.load(f)
            # Convert string keys back to integers
            return {int(k): v for k, v in cities_data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cities():
    with open(CITIES_FILE, 'w') as f:
        # Convert integer keys to strings for JSON serialization
        cities_data = {str(k): v for k, v in user_cities.items()}
        json.dump(cities_data, f, indent=4)

# Load cities from the file when the bot starts (only once)
user_cities = load_cities()

# Main menu keyboard with the new buttons
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Manual Event Updates Check")],
        [KeyboardButton(text="City Management")],
        [KeyboardButton(text="Profile")]
    ],
    resize_keyboard=True
)

# Define a dictionary to track user states
user_states = {}

# Start command handler
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    
    # Initialize the user in the cities file if they do not exist
    if user_id not in user_cities:
        user_cities[user_id] = []  # Initialize user's city list if it doesn't exist
        save_cities()  # Save the data only once when the user is first added

    await message.reply(
        "Welcome! Choose an option:", 
        reply_markup=main_menu
    )

# Handler for the "City Management" button
@dp.message(F.text == "City Management")
async def city_management(message: types.Message):
    city_management_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="View Cities")],
            [KeyboardButton(text="Add City")],
            [KeyboardButton(text="Remove City")],
            [KeyboardButton(text="Back to Main Menu")]
        ],
        resize_keyboard=True
    )
    await message.reply("Choose a city management option:", reply_markup=city_management_menu)

# Handler for the "Back to Main Menu" button
@dp.message(F.text == "Back to Main Menu")
async def back_to_main_menu(message: types.Message):
    await message.reply("Returning to the main menu...", reply_markup=main_menu)

# Handler for viewing cities
@dp.message(F.text == "View Cities")
async def view_cities(message: types.Message):
    user_id = message.from_user.id
    cities = user_cities.get(user_id, [])

    if not cities:
        await message.reply("No cities in the list yet.")
    else:
        city_list = "\n".join(cities)
        await message.reply(f"Current cities:\n{city_list}")

# Handler for adding a city
@dp.message(F.text == "Add City")
async def start_add_city(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = 'adding_city'  # Set user state to 'adding_city'
    await message.reply("Please enter the name of the city to add:")

# Text handler for adding city
@dp.message(F.text)
async def add_city(message: types.Message):
    user_id = message.from_user.id
    city = message.text.strip()

    # Prevent conflicts with menu buttons
    if city in ["View Cities", "Add City", "Remove City", "Back to Main Menu", "Manual Event Updates Check", "Profile"]:
        return  # Do not add these as cities

    # Only allow adding city if the user is in the 'adding_city' state
    if user_states.get(user_id) == 'adding_city':
        cities = user_cities.get(user_id, [])

        if city in cities:
            await message.reply(f"{city} is already in the list.")
        else:
            cities.append(city)  # Update the user's city list
            user_cities[user_id] = cities  # Update user cities in memory
            save_cities()  # Save to the file after the update
            await message.reply(f"{city} has been added to the list.")

        # Reset user state after adding a city
        user_states[user_id] = None
        

@dp.message(F.text == "Remove City")
async def start_remove_city(message: types.Message):
    user_id = message.from_user.id
    cities = user_cities.get(user_id, [])
    print("balls")

    if not cities:
        await message.reply("The city list is empty. Nothing to remove.")
        return

    # Create an inline keyboard with city buttons
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=city, callback_data=f"remove_{city}")]
            for city in cities
        ]
    )

    await message.reply("Select a city to remove:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith('remove_'))
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data.split("_", 1)[1]  # Extract city name from callback data

    cities = user_cities.get(user_id, [])

    if city in cities:
        cities.remove(city)  # Remove the city from the list
        user_cities[user_id] = cities  # Update the user's cities list
        save_cities()  # Save the updated list to the file

        # First, acknowledge the callback
        await callback_query.answer(f"Removed {city}")

        # Now, send a new message asking to select a city to remove again
        if cities:
            # Create a new keyboard with remaining cities
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=remaining_city, callback_data=f"remove_{remaining_city}")]
                    for remaining_city in cities
                ]
            )
            await callback_query.message.answer(
                "Select another city to remove:",
                reply_markup=keyboard
            )
        else:
            await callback_query.message.answer("All cities have been removed.")
            await callback_query.message.answer("Press 'Remove City' again to start removing cities from your list.")
    else:
        await callback_query.answer(f"{city} was not found in your list")



# Handler for the "Profile" button
@dp.message(F.text == "Profile")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    await message.reply(f"Your user ID: {user_id}\nYour username: {username}")

# Main function to start the bot
async def main():
    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)

    # Start polling for updates
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())