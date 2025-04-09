import time
import json
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import html

# Function to log the script process and track its progress
def log(message):
    print(f"LOG: {message}")

# Parse command line arguments
parser = argparse.ArgumentParser(description="Scrape Marvel Strike Force data")
parser.add_argument("--max-pages", type=int, default=7, help="Number of pages to scrape (default is 7)")
args = parser.parse_args()

# Web scraping setup
log("Starting the web scraping process...")
url = "https://marvelstrikeforce.com/en/meta/iso"
headers = {"User-Agent": "Mozilla/5.0"}

options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run headless to avoid UI loading
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Navigate to the first page
driver.get(url)
log("Waiting for the page to load...")

# Add an explicit wait for the table to load (e.g., waiting for the table element to be visible)
try:
    table_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "table"))
    )
    log("Table loaded.")
except Exception as e:
    log(f"Error waiting for table: {e}")

# Give the page a bit more time to load completely (optional, for safety)
time.sleep(3)

# Initialize lists to hold data
iso_data = []
character_iso = []

# Dictionary to store the unique ISO-8 descriptions (since they are the same for every character)
iso_descriptions = {}

# Loop through pages (up to max-pages set in the command line argument)
for page_num in range(1, args.max_pages + 1):  # Use max-pages argument for testing
    log(f"Processing page {page_num}...")

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Target rows inside the <tbody> tag, as the actual table rows are likely inside it
    table_body = soup.find("tbody")
    rows = table_body.find_all("tr") if table_body else []

    log(f"Found {len(rows)} rows on page {page_num}.")

    # Process each character on the page
    for row in rows:
        iso_classes = []
        character_name = None

        # Try to find the character name in the data-original-title attribute of the <a> tag
        character_cell = row.find("td", {"data-label": "Character"})
        if character_cell:
            character_link = character_cell.find("a")
            if character_link:
                character_name = character_link.get("data-original-title", "").strip()  # Get the name from data-original-title
            else:
                character_name = None
        else:
            character_name = None

        log(f"Character name found: {character_name}")

        # Skip this row if no character name was found
        if not character_name:
            continue

        # TESTING AREA *********************************************
        # 


        # Continue with the ISO-8 class extraction and data collection
        for index in range(1, 6):  # We have 5 choices per character
            iso_cell = row.find_all("td", {"data-label": f"{index}th"})

            # Check if the cell exists and contains the ISO-8 class information
            if iso_cell:
                iso_cell = iso_cell[0]  # Get the first matching cell
                iso_class_name = iso_cell.find("span", class_="user-class").text.strip() if iso_cell.find("span", class_="user-class") else None
                
                log(f"ISO Class Name Found: {iso_class_name}")

                # Check if the div with the iso-wrapper class exists
                iso_wrapper = iso_cell.find("div", class_="iso-wrapper")
                if iso_wrapper:
                    # Extract the raw HTML from the data-original-title attribute
                    raw_description = iso_wrapper.get("data-original-title", "").strip()

                    # Decode the HTML entities (e.g., &lt; to <, &gt; to >)
                    decoded_description = html.unescape(raw_description)
                    
                    # Parse the decoded HTML using BeautifulSoup
                    soup_description = BeautifulSoup(decoded_description, "html.parser")
                    
                    # Extract the clean text (description) from the parsed HTML, ignoring tags
                    iso_class_description = soup_description.get_text(separator=" ").strip()
                    
                    log(f"Extracted Raw Description: {raw_description}")
                    log(f"Decoded Description: {decoded_description}")
                    log(f"Soup Description: {soup_description}")
                    log(f"ISO Class Description: {iso_class_description}")
                else:
                    # If the wrapper is not found, set default values
                    log("ISO Wrapper not found, using default values.")
                    iso_class_name = None
                    iso_class_description = None

                # If both the name and description are available, store them
                if iso_class_name and iso_class_description:
                    # If it's the first time we encounter this ISO-8 class, store the description
                    if iso_class_name not in iso_descriptions:
                        iso_descriptions[iso_class_name] = iso_class_description

                    # Add this class to the iso_classes list in the correct order
                    iso_classes.append(iso_class_name)

        # Log the final ISO classes for debugging
        log(f"Extracted ISO Classes for {character_name}: {iso_classes}")

        # Add ISO class data to the iso_data list if the class exists
        for iso_class_name, iso_class_description in iso_descriptions.items():
            iso_data.append({
                "class": iso_class_name,
                "description": iso_class_description
            })

        # Add the character's ISO class preferences (Top Choice, 2nd, etc.) to the character_iso list
        character_iso.append({
            "name": character_name,
            "Top Choice": iso_classes[0] if len(iso_classes) > 0 else None,
            "2nd": iso_classes[1] if len(iso_classes) > 1 else None,
            "3rd": iso_classes[2] if len(iso_classes) > 2 else None,
            "4th": iso_classes[3] if len(iso_classes) > 3 else None,
            "5th": iso_classes[4] if len(iso_classes) > 4 else None
        })

    # Check if there's a next page, and click on it if it's clickable
    try:
        # Locate the next page button and wait for it to be visible
        next_page_button = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "pagination-next"))
        )

        # Scroll the page so that the next button is in view
        driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)

        # Check if the 'Next' button is not disabled
        if "disabled" not in next_page_button.get_attribute("class"):
            # Try to click it using JavaScript
            driver.execute_script("arguments[0].click();", next_page_button)
            log(f"Moving to page {page_num + 1}...")
            time.sleep(3)  # Wait for the next page to load
        else:
            log("No more pages left to scrape.")
            break
    except Exception as e:
        log(f"Error finding next page button: {e}")
        break

# After scraping all the pages, save the data
log("Saving ISO-8 data and character ISO preferences to JSON file...")

# Prepare the final output structure
output_data = {
    "iso_data": iso_data,
    "character_iso": character_iso
}

# Save the data to a JSON file
with open("src/assets/iso_data.json", "w", encoding="utf-8") as json_file:
    json.dump(output_data, json_file, indent=4)

log("✅ Scraping and data processing completed successfully!")

# Close the WebDriver after completion
driver.quit()
