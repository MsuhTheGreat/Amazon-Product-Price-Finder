import os
import json
import shutil
from time import sleep, time
from random import randint
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
import pandas as pd
import subprocess
import psutil
import sys
from pathlib import Path

# Load environment variables
load_dotenv(".env")

# Global constants from environment variables
# DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
ALERTZY_URL         = "https://alertzy.app/send"
ALERTZY_ACCOUNT_KEY = os.getenv("ALERTZY_ACCOUNT_KEY", "")
CHROME_DATA_DIR     = os.getenv("CHROME_DATA_DIR", "")
CHROME_PROFILE      = os.getenv("CHROME_PROFILE", "")
SPREADSHEET_ID      = os.getenv("SPREADSHEET_ID", "")
HEADLESS            = os.getenv("HEADLESS", "false")
# CHROME_PATH = os.getenv("CHROME_PATH", "chrome.exe")

# Converting paths into Path objects
CHROME_DATA_DIR = Path(CHROME_DATA_DIR)
CHROME_PROFILE = Path(CHROME_PROFILE)

# Check if environment variables are absent
if not ALERTZY_ACCOUNT_KEY or not CHROME_DATA_DIR or not CHROME_PROFILE or not SPREADSHEET_ID or not os.path.exists("service_account.json"):
    if not ALERTZY_ACCOUNT_KEY:                    print("❌ Alertzy Account Key is not set. Set it inside the .env file.")
    if not CHROME_DATA_DIR:                        print("❌ Chrome Data Directory is not set. Set it inside the .env file.")
    if not CHROME_PROFILE:                         print("❌ Chrome Profile is not set. Set it inside the .env file.")
    if not SPREADSHEET_ID:                         print("❌ Spreadsheet ID is not set. Set it inside the .env file.")
    if not os.path.exists("service_account.json"): print("❌ Service Account JSON file not found. Create 'service_account.json' first.")
    print("Scraper Exiting now...")
    sys.exit(1)


def initialize_project():
    """Initial setup: Create directories and initialize items.json if not present."""
    os.makedirs("old", exist_ok=True)
    os.makedirs("new", exist_ok=True)
    if not os.path.exists("items.json"):
        with open("items.json", "w") as file:
            json.dump([], file, indent=4)


def find_text(parent, by, value):
    """
    Find text for an element.

    Args:
        parent (WebElement): The parent element to search within.
        by (By): The locator strategy to use.
        value (str): The value of the locator to search for.

    Returns:
        str: The extracted text, or "N/A" if not found.
    """
    try:
        return parent.find_element(by, value).text.strip()
    # except NoSuchElementException:
    #     return "N/A"
    except Exception as e:
        print(f"❌ {e}")
        print("-" * 40)
        return "N/A"


def scrap_products(wait, title_lst, price_lst, asin_lst):
    """
    Scrape product details (title, price, and ASIN) from the current page.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        wait (WebDriverWait): WebDriverWait instance for waiting for elements.
        title_lst (list): List to store product titles.
        price_lst (list): List to store product prices.
        asin_lst (list): List to store ASINs.
    """
    products_xpath = '//div[@data-component-type="s-search-result"]'
    products = wait.until(EC.presence_of_all_elements_located((By.XPATH, products_xpath)))

    for product in products:
        title = find_text(product, By.TAG_NAME, 'h2')
        price_whole = find_text(product, By.CLASS_NAME, 'a-price-whole').replace(",", "")
        price_fraction = find_text(product, By.CLASS_NAME, 'a-price-fraction')
        
        if price_whole == "N/A":
            print("❌ Skipping product with missing price")
            print("-" * 40)
            continue
        
        price = f"{price_whole}.{price_fraction if price_fraction != 'N/A' else '00'}"
        price = float(price)
        asin = product.get_attribute("data-asin")

        title_lst.append(title)
        price_lst.append(price)
        asin_lst.append(asin)

        print(f"Title: {title}")
        print(f"Price: {price}")
        print(f"ASIN: {asin}")
        print("-" * 40)


def send_alert(message):
    """
    Send an alert using the Alertzy API.

    Args:
        message (str): The message to send.
    """
    group = "My Amazon Scraper"
    params = {
        "accountKey": ALERTZY_ACCOUNT_KEY,
        "title": "Dropage In Prices",
        "message": message,
        "group": group
    }

    try:
        response = requests.post(url=ALERTZY_URL, json=params)
        response.raise_for_status()
        print(response.text)
        print("Message Sent!")
    except Exception as e:
        print(f"❌ {e}")
        print("-" * 40)


def upload_df_to_gsheet(df, sheet_name):
    """
    Upload a DataFrame to a Google Sheets document.

    Args:
        df (DataFrame): The DataFrame to upload.
        sheet_name (str): The name of the sheet in the spreadsheet.
    """
    # if not os.path.exists("service_account.json"):
    #     print("❌ Service Account JSON file not found. Create 'service_account.json' first.")
    #     print("❌ Uploading to Google Sheets failed.")
    #     print("-" * 40)
    #     return
    for i in range(3):
        try:
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json",
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=creds)
            spreadsheet_id = os.getenv("SPREADSHEET_ID")

            # Convert DataFrame to list of lists
            values = [df.columns.tolist()] + df.values.tolist()

            # Delete sheet if it exists
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break

            if sheet_id is not None:
                batch_update_request = {
                    "requests": [
                        {"deleteSheet": {"sheetId": sheet_id}}
                    ]
                }
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=batch_update_request
                ).execute()

            # Add new sheet
            add_sheet_request = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name
                            }
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=add_sheet_request
            ).execute()

            # Upload data
            range_name = f"{sheet_name}!A1"
            body = {
                "values": values
            }
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()

            print(f"✅ Uploaded to Google Sheet tab: {sheet_name}")

        except Exception as e:
            print(f"❌ An error occurred: {e}")
        if i != 2:
            print("🔁 Retrying...")
            sleep(2)
        else: print("❌ Failed to upload after 3 retries.")
        print("-" * 40)


# def create_new_profile():
#     """Creates a new Chrome profile using Chrome's command line."""
#     chrome_path = rf"{CHROME_PATH}"
#     chrome_data_dir = os.getenv("CHROME_DATA_DIR")
#     chrome_profile = os.getenv("CHROME_PROFILE", "Default")

#     profile_path = os.path.join(chrome_data_dir, chrome_profile)

#     # Ensure we have the proper directory
#     if not os.path.exists(chrome_data_dir):
#         os.makedirs(chrome_data_dir)

#     # Remove old profile if it exists
#     if os.path.exists(profile_path):
#         shutil.rmtree(profile_path)

#     print(f"Creating Chrome profile: {chrome_profile}")
#     try:
#         subprocess.run([
#             "chrome",
#             f"--user-data-dir={chrome_data_dir}",
#             f"--profile-directory={chrome_profile}",
#             "--headless",
#             "--disable-gpu",
#             "about:blank"
#         ], timeout=3, check=True)
#         print(f"Profile {chrome_profile} created successfully!")
#     except Exception as e:
#         print(f"Error running subprocess: {e}")


# def kill_chrome_processes():
#     """Kill any running Chrome processes."""
#     try:
#         for proc in psutil.process_iter(attrs=['pid', 'name']):
#             if 'chrome' in proc.info['name'].lower():
#                 proc.kill()
#                 print(f"Killed Chrome process: {proc.info['pid']}")

#     except psutil.NoSuchProcess as e:
#         print(f"Error: No such process found - {e}")
#     except psutil.AccessDenied as e:
#         print(f"Error: Access denied to kill process - {e}")
#     except psutil.ZombieProcess as e:
#         print(f"Error: Zombie process encountered - {e}")
#     except Exception as e:
#         print(f"Unexpected error: {e}")


# def setup_chrome_profile():
#     """Setup Chrome profile for manual login and CAPTCHA handling."""
#     print("\nLaunching Chrome for manual profile setup...")
#     options = ChromeOptions()
#     options.add_argument(f"--user-data-dir={CHROME_DATA_DIR}")
#     options.add_argument(f"--profile-directory={CHROME_PROFILE}")
    
#     driver = Chrome(options=options)
#     driver.get("https://www.google.com/")

#     input("🔒 Please log in and set up your Chrome profile. Also sign in to Chrome and solve the Amazon CAPTCHA. It is a must.\n✅ Press Enter when you're finished: ")

#     try:
#         driver.quit()
#         print("✅ Profile setup complete and browser closed.")
#     except Exception as e:
#         print(f"⚠️ Error during profile setup shutdown: {e}")


def create_new_profile():
    """
    Creates a new Chrome profile directory and prompts the user to configure it manually.
    """
    profile_path = CHROME_DATA_DIR / CHROME_PROFILE

    if not os.path.exists(CHROME_DATA_DIR):
        os.makedirs(CHROME_DATA_DIR)

    if os.path.exists(profile_path):
        shutil.rmtree(profile_path)

    print(f"Creating Chrome profile: {CHROME_PROFILE}")
    print("🔒 Please log in to your Google Account. Then go to Amazon and accept cookies. You do not need to sign into Amazon. This is a one-time setup requirement.\n")
    sleep(2)
    print("Creating Chrome Profile...")
    sleep(2)
    print(f"✅ Profile '{CHROME_PROFILE}' created successfully!")
    sleep(1)


def main():
    """Main execution loop of the Amazon price scraper."""
    initialize_project()

    with open("items.json", "r") as file:
        items = json.load(file)

    while True:
        print(f"Items to Search: {items}")
        user = input("Do you want to remove or add any item from the list? If no, enter 'no'. If want to add, enter 'add'. If want to remove, enter 'remove'.\nEnter your choice: ").lower()
        if user == "no":
            with open("items.json", "w") as file:
                json.dump(items, file, indent=4)
            break
        elif user == "add":
            item = input("Enter item name: ")
            if item not in items:
                items.append(item)
            print("Done!")
        elif user == "remove":
            item = input("Enter item name: ")
            if item in items:
                items.remove(item)
            else:
                print("Item not in list.")
        else:
            print("Behave yourself!")

    for item in items:
        while True:
            driver = None
            try:
                options = ChromeOptions()
                headless = HEADLESS
                profile_path = CHROME_DATA_DIR / CHROME_PROFILE

                if not os.path.exists(profile_path):
                    create_new_profile()
                    headless = "false"

                options.add_argument(f"--user-data-dir={CHROME_DATA_DIR}")
                options.add_argument(f"--profile-directory={CHROME_PROFILE}")
                
                if headless.lower() == "true":
                    options.add_argument("--headless")
                print(f"Headless mode is set to: {headless}")

                search = item

                driver = Chrome(options=options)
                web = "https://www.amazon.com/"
                driver.get(web)

                wait = WebDriverWait(driver, 20)

                search_xpath = '//input[@placeholder="Search Amazon" or @aria-label="Search"]'
                search_box = wait.until(EC.presence_of_element_located((By.XPATH, search_xpath)))
                search_box.send_keys(search + Keys.ENTER)

                title_lst = []
                price_lst = []
                asin_lst = []
                next_button_xpath = '//a[contains(@class, "s-pagination-next")]'
                for i in range(3):
                    scrap_products(wait, title_lst, price_lst, asin_lst)
                    try:
                        next_button = wait.until(EC.presence_of_element_located((By.XPATH, next_button_xpath)))
                        next_button.click()
                        sleep(randint(2, 5))
                    except Exception as e:
                        print(f"🛑 No more pages or error in pagination: {e}")
                        print("-" * 40)
                        break

                df = pd.DataFrame({
                    "Title": title_lst,
                    "Price": price_lst,
                    "ASIN": asin_lst
                })

                df.to_excel(f"new/{search.replace(' ', '_')}.xlsx", index=False, engine="openpyxl")

                if os.path.exists(f"old/{search.replace(' ', '_')}.xlsx"):
                    old_df = pd.read_excel(f"old/{search.replace(' ', '_')}.xlsx")

                    merged_df = df.merge(old_df, on="ASIN", suffixes=("_new", "_old"))
                    merged_df = merged_df[merged_df["Price_old"] != 0]
                    merged_df["Price_Drop_%"] = (merged_df["Price_new"] - merged_df["Price_old"]) / merged_df["Price_old"] * 100
                    significant_drops = merged_df[merged_df["Price_Drop_%"] >= 10]
                    if not significant_drops.empty:
                        message_lines = []
                        for _, row in significant_drops.iterrows():
                            line = f"{row['Title_new']}\nOld Price: {row['Price_old']:.2f}\nNew Price: {row['Price_new']:.2f}\nASIN: {row['ASIN']}"
                            message_lines.append(line)
                        message = "\n\n\n".join(message_lines)
                        send_alert(message)

                df.to_excel(f"old/{search.replace(' ', '_')}.xlsx", index=False, engine="openpyxl")

                upload_df_to_gsheet(df, item)
                sleep(randint(2, 7))

            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                if driver:
                    driver.quit()
                print("-" * 40)


if __name__ == "__main__":
    tic = time()
    main()
    toc = time()
    print(f"Program executing time: {round((toc-tic) / 60, 2)} min")
