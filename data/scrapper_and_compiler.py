import pandas as pd
import json
import re
import time
import os
import argparse  # For parsing command line arguments
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from collections import Counter

# Function to log the script process and track its progress
def log(message):
    print(f"LOG: {message}")

# Set up command-line argument parsing
def parse_args():
    parser = argparse.ArgumentParser(description="Web Scraper for Marvel Strike Force Characters")
    parser.add_argument("-testing", type=int, help="Number of characters to scrape for testing", default=None)
    return parser.parse_args()

# Example of how to upload data to Firestore
def upload_to_firestore(data, collection_name):
    """
    Uploads the given data to Firestore in the specified collection.
    """
    collection_ref = db.collection(collection_name)
    for item in data:
        collection_ref.add(item)

# Load environment variables from the .env file
load_dotenv()

# Get the Firebase service account key path from the environment variable
service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
log("Firebase service account path: " + service_account_path)

# Initialize Firebase Admin SDK
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()
log("Firebase Admin SDK initialized.")

# Get the directory of the current script
script_dir = os.path.dirname(os.path.realpath(__file__))

# Web scraping setup
args = parse_args()  # Get arguments passed via command line
testing_limit = args.testing  # Get the number of characters to scrape for testing

log("Starting the web scraping process...")
log("Testing limit set to: " + str(testing_limit) if testing_limit else "No testing limit set.")
log("Scrapper working directory: " + os.getcwd())
log("Script directory: " + script_dir)
url = "https://marvelstrikeforce.com/en/characters"
headers = {"User-Agent": "Mozilla/5.0"}

options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run headless to avoid UI loading
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Visit the page with character data
driver.get(url)
log("Waiting for the page to load...")
time.sleep(3)  # Wait for the page to load fully

# Parse the page with BeautifulSoup
log("Parsing the page with BeautifulSoup...")
soup = BeautifulSoup(driver.page_source, "html.parser")
character_section = soup.body.find("section")
characters = character_section.find_all("li", class_="character")

# Load Excel Data
log("Loading Excel data...")
xlsx_data = pd.read_excel("data/CHARACTER_STAT_DATA.xlsx", sheet_name="in")
excel_data = xlsx_data.rename(columns=lambda x: x.strip().replace("\xa0", "")).to_dict(orient="records")

# Function to extract abilities
def extract_abilities(text):
    """
    Extracts abilities from a raw scraped text.
    """
    abilities = {}
    text = text.replace("Character Abilities", "").strip()
    # ability_names = re.findall(r'([A-Z][a-zA-Z\'’\-\s]+)\s{2,}', text)
    ability_chunks = re.split(r'([A-Z][a-zA-Z\'’\-\s]+)\s{2,}', text)[1:]

    for i in range(0, len(ability_chunks), 2):
        ability_name = ability_chunks[i].strip()
        ability_description = ability_chunks[i + 1].strip() if i + 1 < len(ability_chunks) else ""
        abilities[ability_name] = ability_description

    return abilities

# Function to get character stats from the Excel data
def get_character_stats(name):
    """
    Matches the character name with the stats in the Excel dataset.
    """
    for entry in excel_data:
        if entry.get("CHARACTERS") == name.upper():
            return {k: v for k, v in entry.items() if k not in ["CHARACTERS", "#"]}
    return {}

# Prepare to store the character data
compiled_characters = {}
log("Starting to process character data...")

# Limit the scraping to `testing_limit` characters if set
scraped_count = 0

for char in characters:
    if testing_limit and scraped_count >= testing_limit:
        log(f"Reached testing limit of {testing_limit} characters. Exiting...")
        break  # Stop scraping after reaching the limit

    name = char.find("h4").text.strip()
    link = char.find("a")["href"]
    
    log(f"Processing character: {name}")
    
    # Navigate to the individual character page
    driver.get("https://marvelstrikeforce.com" + link)
    time.sleep(3)  # Wait for the character page to load

    character_soup = BeautifulSoup(driver.page_source, "html.parser")
    character_section = character_soup.body.find("section")
    traits = character_section.find_all("a", class_="traits")
    abilities = character_section.find("div", class_="hero-abilities")
    description = character_section.find("div", class_="description")
    image_wrapper = character_section.find("div", class_="portrait-wrapper is-unselectable")

    # Extract abilities, stats, and image URL
    cleaned_abilities = extract_abilities(abilities.text.strip() if abilities else "")
    stats = get_character_stats(name)

    compiled_characters[name] = {
        "id": hash(name),
        "name": name,
        "stats": stats,
        "abilities": cleaned_abilities,
        "path": link,
        "imageUrl": image_wrapper.find("img")["src"] if image_wrapper else None,
        "traits": [trait.text.strip() for trait in traits],
        "description": description.text.strip() if description else "No description available"
    }

    # Increment the counter
    scraped_count += 1

# Construct paths relative to the script's location
json_output_path = os.path.join(script_dir, "..", "src", "assets", "compiled_characters.json")
with open(json_output_path, "w", encoding="utf-8") as json_file:
    json.dump(list(compiled_characters.values()), json_file, indent=4)

# Log completion
log("Data collection and processing complete.")
log("Scraped data saved to 'compiled_characters.json'.")

log("Uploading data to Firestore...")
upload_to_firestore(compiled_characters.values(), "characters")
log("Data uploaded to Firestore successfully.")


# Optionally: Create a list of most common abilities (tag cloud)
log("Generating most common abilities for filtering...")
abilities_counter = Counter()

for char in compiled_characters.values():
    for ability in char["abilities"]:
        abilities_counter[ability] += 1

# Store the top 100 most common abilities
# Construct paths relative to the script's location
json_output_path = os.path.join(script_dir, ".." , "src", "assets", "common_abilities.json")
with open(json_output_path, "w", encoding="utf-8") as json_file:
    json.dump(list(compiled_characters.values()), json_file, indent=4)

log("Tag cloud generation complete.")

# Close the WebDriver
driver.quit()

log("✅ Scraping and data processing completed successfully!")
