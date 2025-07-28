"""
Amazon Price Tracker Bot
--------------------------
Scrapes Amazon product prices using Selenium and notifies users of significant drops.
Data is saved locally and synced with a Google Sheet.

Features:
- Persistent Chrome profile using undetected_chromedriver
- Google Sheets API integration for cloud sync
- Alertzy notifications for price drops
- Supports product search customization
- Detects and compares old vs new product prices
"""

# ----------------------------------------
# Imports
# ----------------------------------------

import os
import json
import shutil
import sys
from time import sleep, time
from random import randint
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ----------------------------------------
# Constants and Configuration
# ----------------------------------------

load_dotenv(".env")

# Environment variables
ALERTZY_ACCOUNT_KEY  = os.getenv("ALERTZY_ACCOUNT_KEY", "")
CHROME_DATA_DIR      = Path(os.getenv("CHROME_DATA_DIR", ""))
CHROME_PROFILE       = Path(os.getenv("CHROME_PROFILE", ""))
SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "")
HEADLESS             = os.getenv("HEADLESS", "false").lower()
ALERTZY_URL          = "https://alertzy.app/send"
WAIT_TIME            = 20
PERCENTAGE_THRESHOLD = input("Enter the percentage dropdown you want to recieve notifications for: ")
try: PERCENTAGE_THRESHOLD = float(PERCENTAGE_THRESHOLD)
except: PERCENTAGE_THRESHOLD = 10

# Exit if required env vars are missing
if not ALERTZY_ACCOUNT_KEY or not CHROME_DATA_DIR or not CHROME_PROFILE or not SPREADSHEET_ID or not os.path.exists("service_account.json"):
    if not ALERTZY_ACCOUNT_KEY:                    print("❌ Alertzy Account Key is not set. Set it inside the .env file.")
    if not CHROME_DATA_DIR:                        print("❌ Chrome Data Directory is not set. Set it inside the .env file.")
    if not CHROME_PROFILE:                         print("❌ Chrome Profile is not set. Set it inside the .env file.")
    if not SPREADSHEET_ID:                         print("❌ Spreadsheet ID is not set. Set it inside the .env file.")
    if not os.path.exists("service_account.json"): print("❌ Service Account JSON file not found. Create 'service_account.json' first and place it in the directory.")
    sys.exit("❌ Exiting... Please fix your environment setup.")

# ----------------------------------------
# Utilities
# ----------------------------------------

def initialize_project():
    """Create necessary folders and initialize `items.json` if not present."""
    os.makedirs("old", exist_ok=True)
    os.makedirs("new", exist_ok=True)
    if not os.path.exists("items.json"):
        with open("items.json", "w") as f:
            json.dump([], f, indent=4)

def find_text(parent, by, value):
    """
    Extracts text from an element, returning 'N/A' if not found.

    Args:
        parent (WebElement): Parent element.
        by (By): Locator strategy.
        value (str): Locator value.

    Returns:
        str: Extracted text or 'N/A'.
    """
    try:
        return parent.find_element(by, value).text.strip()
    except NoSuchElementException:
        return "N/A"
    except Exception as e:
        print(f"❌ Error in find_text function: {e}")
        print("-" * 40)
        return "N/A"

def create_new_profile():
    """
    Initializes a new Chrome user profile for Amazon.
    Requires user to manually accept cookies on Amazon.
    """
    profile_path = CHROME_DATA_DIR / CHROME_PROFILE

    if not CHROME_DATA_DIR.exists():
        CHROME_DATA_DIR.mkdir(parents=True)

    if profile_path.exists():
        shutil.rmtree(profile_path)

    print(f"🔐 Creating Chrome profile: {CHROME_PROFILE}")
    print("🥇 Log into your Google account.")
    print("🥈 Visit Amazon and accept cookies. (optional)")
    print("🥉 Close browser once done.\n")

    options = ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_DATA_DIR}")
    options.add_argument(f"--profile-directory={CHROME_PROFILE}")
    driver = Chrome(options=options)

    try:
        while True:
            driver.title  # Keeps session alive until closed
            sleep(0.5)
    except:
        driver.quit()
        print("✅ Chrome profile setup completed.")

# ----------------------------------------
# Scraping Functions
# ----------------------------------------

def scrap_products(wait, title_lst, price_lst, asin_lst):
    """
    Scrapes products from current Amazon search results page.

    Args:
        wait (WebDriverWait): Selenium wait instance.
        title_lst (list): Output list for product titles.
        price_lst (list): Output list for prices.
        asin_lst (list): Output list for ASINs.
    """
    product_selector = '//div[@data-component-type="s-search-result"]'
    products = wait.until(EC.presence_of_all_elements_located((By.XPATH, product_selector)))

    for product in products:
        title = find_text(product, By.TAG_NAME, 'h2')
        price_whole = find_text(product, By.CLASS_NAME, 'a-price-whole').replace(",", "")
        price_fraction = find_text(product, By.CLASS_NAME, 'a-price-fraction')

        if price_whole == "N/A":
            print("⚠️ Skipping product with no price")
            print("-" * 40)
            continue

        price = float(f"{price_whole}.{price_fraction if price_fraction != 'N/A' else '00'}")
        asin = product.get_attribute("data-asin")

        title_lst.append(title)
        price_lst.append(price)
        asin_lst.append(asin)

        print(f"🛒 {title}")
        print(f"💲 {price}")
        print(f"🔗 ASIN: {asin}")
        print("-" * 40)

def send_alert(message):
    """
    Sends a price drop notification via Alertzy.

    Args:
        message (str): Message to send.
    """
    payload = {
        "accountKey": ALERTZY_ACCOUNT_KEY,
        "title": "Dropage In Prices",
        "message": message,
        "group": "My Amazon Scraper"
    }

    try:
        response = requests.post(ALERTZY_URL, json=payload)
        response.raise_for_status()
        print(f"📲 Notification successfully sent to your Alertzy account due to a price drop of {PERCENTAGE_THRESHOLD}% or more since your last check.")
    except Exception as e:
        error_str = str(e)
        if ALERTZY_API_KEY in error_str:
            error_str = error_str.replace(ALERTZY_API_KEY, "[SECRET]")
        print(f"❌ Failed to send alert: {error_str}")
        print("-" * 40)

def upload_df_to_gsheet(df, sheet_name):
    """
    Uploads a DataFrame to Google Sheets.

    Args:
        df (pd.DataFrame): Data to upload.
        sheet_name (str): Tab name.
    """
    for attempt in range(3):
        try:
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json",
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=creds)

            # Delete existing sheet
            spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID,
                        body={"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
                    ).execute()
                    break

            # Add new sheet
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
            ).execute()

            # Upload values
            values = [df.columns.tolist()] + df.values.tolist()
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": values}
            ).execute()

            print(f"✅ Data uploaded to sheet: {sheet_name}")
            return

        except Exception as e:
            print(f"❌ Upload attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                print("🔁 Retrying...\n")
                sleep(2)
            else:
                print("🛑 Giving up after 3 attempts.")
    print("-" * 40)

# ----------------------------------------
# Main Program
# ----------------------------------------

def main():
    """Main scraping and comparison loop."""
    initialize_project()

    with open("items.json", "r") as file:
        items = json.load(file)

    # Allow user to edit product list
    while True:
        print(f"\n📦 Items to Search: {items}")
        choice = input("Type 'no' to continue, 'add' to add item, 'remove' to remove item: ").lower()
        if choice == "no":
            break
        elif choice == "add":
            item = input("Enter item name: ")
            if item not in items: items.append(item)
        elif choice == "remove":
            item = input("Enter item name: ")
            if item in items: items.remove(item)
        else:
            print("⚠️ Invalid input.")
    with open("items.json", "w") as file:
        json.dump(items, file, indent=4)

    # Profile setup
    if not (CHROME_DATA_DIR / CHROME_PROFILE).exists():
        create_new_profile()

    # Search each item
    for item in items:
        driver = None
        try:
            options = ChromeOptions()
            options.add_argument(f"--user-data-dir={CHROME_DATA_DIR}")
            options.add_argument(f"--profile-directory={CHROME_PROFILE}")
            if HEADLESS == "true":
                options.add_argument("--headless=new")
            driver = Chrome(options=options)
            wait = WebDriverWait(driver, WAIT_TIME)

            driver.get("https://www.amazon.com/")
            search_selector = '//input[contains(@placeholder, "Search Amazon") or contains(@aria-label, "Search") or contains(@id, "nav-bb-search")]'
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, search_selector)))
            search_box.send_keys(item + Keys.ENTER)

            title_lst, price_lst, asin_lst = [], [], []
            for _ in range(3):  # scrape 3 pages
                scrap_products(wait, title_lst, price_lst, asin_lst)
                try:
                    next_button_selector = '//a[contains(@class, "s-pagination-next")]'
                    next_button = wait.until(EC.presence_of_element_located((By.XPATH, next_button_selector)))
                    next_button.click()
                    sleep(randint(2, 5))
                except Exception as e:
                    print(f"🛑 No more pages or error in pagination: {e}")
                    print("-" * 40)
                    break

            df = pd.DataFrame({"Title": title_lst, "Price": price_lst, "ASIN": asin_lst})
            search_tag = item.replace(" ", "_")

            df.to_excel(f"new/{search_tag}.xlsx", index=False, engine="openpyxl")

            # Compare with old prices
            old_path = f"old/{search_tag}.xlsx"
            if os.path.exists(old_path):
                old_df = pd.read_excel(old_path)
                merged = df.merge(old_df, on="ASIN", suffixes=("_new", "_old"))
                merged = merged[merged["Price_old"] != 0]
                merged["Price_Drop_%"] = (merged["Price_new"] - merged["Price_old"]) / merged["Price_old"] * 100
                drops = merged[merged["Price_Drop_%"] >= PERCENTAGE_THRESHOLD]
                if not drops.empty:
                    message = "\n\n\n".join(
                        f"{row['Title_new']}\nOld: ${row['Price_old']:.2f}\nNew: ${row['Price_new']:.2f}\nASIN: {row['ASIN']}"
                        for _, row in drops.iterrows())
                    send_alert(message)

            # Save new data
            df.to_excel(old_path, index=False, engine="openpyxl")
            upload_df_to_gsheet(df, item)

            sleep(randint(2, 5))

        except Exception as e:
            print(f"❌ Error while processing '{item}': {e}")
        finally:
            if driver: driver.quit()
            print("-" * 40)

# ----------------------------------------
# Entry Point
# ----------------------------------------

if __name__ == "__main__":
    start = time()
    main()
    end = time()
    print(f"\n⏰ Total Execution Time: {round((end - start) / 60, 2)} minutes")
