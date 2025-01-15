from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import time

# Set Firefox options
options = Options()
options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Set up the Firefox driver using GeckoDriverManager
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)

# Open the Viagogo website
driver.get("https://www.viagogo.com/")

# Wait for the page to load
time.sleep(5)

# Search for a specific event (example: Coldplay concert)
search_box = driver.find_element(By.NAME, "q")
search_box.send_keys("Coldplay")
search_box.submit()

# Scrape ticket prices
time.sleep(5)
tickets = driver.find_elements(By.CLASS_NAME, "Price")

for ticket in tickets:
    print(ticket.text)

# Close the driver
driver.quit()
