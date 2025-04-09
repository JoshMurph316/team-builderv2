import json
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# Function to log the script process and track its progress
def log(message):
    print(f"LOG: {message}")

# Web scraping setup
log("Starting the web scraping process...")
url = "https://marvelstrikeforce.com/en/effects"
headers = {"User-Agent": "Mozilla/5.0"}

options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run headless to avoid UI loading
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Visit the page with the effects data
driver.get(url)
log("Waiting for the page to load...")
time.sleep(3)  # Wait for the page to load fully

# Parse the page with BeautifulSoup
log("Parsing the page with BeautifulSoup...")
soup = BeautifulSoup(driver.page_source, "html.parser")

# Extract effects from the three columns: Positive, Negative, and Other
effects_data = {"positive": [], "negative": [], "other": []}

columns = soup.find_all("div", class_="column")
for column in columns:
    # Get the effect type (Positive, Negative, Other)
    header = column.find("h2", class_="is-unselectable")
    effect_type = header.text.strip().lower() if header else "other"

    # Normalize the effect type to match the dictionary keys
    if "positive" in effect_type:
        effect_type = "positive"
    elif "negative" in effect_type:
        effect_type = "negative"
    else:
        effect_type = "other"
    
    # Find all effects in this column
    effects_list = column.find_all("li", class_="effect")
    for effect in effects_list:
        effect_name = effect.find("h3").text.strip() if effect.find("h3") else "Unnamed Effect"
        effect_description = effect.find("p").text.strip() if effect.find("p") else "No description"
        expires = None
        opposite = None
        
        # Check if there are additional details like Expires or Opposite
        other_info = effect.find("ul", class_="other-info")
        if other_info:
            info_items = other_info.find_all("li")
            for item in info_items:
                text = item.text.strip()
                if "Expires" in text:
                    expires = text.split(":")[-1].strip()
                elif "Opposite" in text:
                    opposite = text.split(":")[-1].strip()

        # Add the effect data to the appropriate category
        effects_data[effect_type].append({
            "name": effect_name,
            "description": effect_description,
            "expires": expires,
            "opposite": opposite
        })

# Log the collected data
log(f"Collected effects data: {effects_data}")

# Save the effects data to JSON file
log("Saving effects data to JSON file...")
with open("src/assets/effects_data.json", "w", encoding="utf-8") as json_file:
    json.dump(effects_data, json_file, indent=4)

log("✅ Effects data collection and saving complete!")

# Close the WebDriver
driver.quit()
