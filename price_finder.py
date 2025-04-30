from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from dotenv import load_dotenv
import os
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from time import sleep
from random import randint
# chrome.exe --user-data-dir="D:/ChromeProfileForAutomation" --profile-directory=FirstAmazonScraperBot
load_dotenv()

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
ALERTZY_ACCOUNT_KEY = os.getenv("ALERTZY_ACCOUNT_KEY")
ALERTZY_URL = "https://alertzy.app/send"
CHROME_DATA_DIR = os.getenv("CHROME_DATA_DIR")
CHROME_PROFILE = os.getenv("CHROME_PROFILE", "Default")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
HEADLESS = os.getenv("HEADLESS", "false")


def initialize_project():
    os.makedirs("old", exist_ok=True)
    os.makedirs("new", exist_ok=True)
    if not os.path.exists("items.json"):
        with open("items.json", "w") as file:
            json.dump([], file, indent=4)


def find_text(parent, by, value):
    try:
        return parent.find_element(by, value).text.strip()
    except NoSuchElementException:
        return "N/A"
    except Exception as e:
        print(f"❌ {e}")
        print("-" * 40)
        return "N/A"


def scrap_products(driver, wait, title_lst, price_lst, asin_lst):
    products_xpath = '//div[@data-component-type="s-search-result"]'
    wait.until(EC.presence_of_all_elements_located((By.XPATH, products_xpath)))
    products = driver.find_elements(By.XPATH, products_xpath)

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
    group = "My Amazon Scraper"
    params = {
        "accountKey": ALERTZY_ACCOUNT_KEY,
        "title": "Dropage In Prices",
        "message": message,
        "group": group
    }

    response = requests.post(url=ALERTZY_URL, json=params)
    response.raise_for_status()
    print(response.text)
    print("Message Sent!")


def upload_df_to_gsheet(df, sheet_name):
    if not os.path.exists("service_account.json"):
        print("Create 'service_account.json' first.")
        return

    creds = service_account.Credentials.from_service_account_file(
        "service_account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    spreadsheet_id = os.getenv("SPREADSHEET_ID")

    # Convert DataFrame to list of lists
    values = [df.columns.tolist()] + df.values.tolist()

    try:
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
        print("-" * 40)

    except HttpError as error:
        print(f"❌ An error occurred: {error}")
        print("-" * 40)


def main():
    initialize_project()
    
    with open("items.json", "r") as file:
        items = json.load(file)

    while True:
        print(f"Items to Search: {items}")
        user = input("Do you want to remove or add any item from the list? If no, enter 'no'. If want to add, enter 'add'. If want to remove, enter 'remove'.\nEnter your choice: ").lower()
        if user == "no": 
            with open ("items.json", "w") as file:
                json.dump(items, file, indent=4)
            break
        elif user == "add":
            item = input("Enter item name: ")
            if item not in items:
                items.append(item)
            print("Done!")
        elif user == "remove":
            item = input("Enter item name: ")
            if item in items: items.remove(item)
            else: print("Item not in list.")
        else:
            print("Behave yourself!")

    for item in items:
        try:
            options = ChromeOptions()
            user_data_dir = rf"{CHROME_DATA_DIR}"
            profile_dir = CHROME_PROFILE
            headless = HEADLESS

            if user_data_dir:
                options.add_argument(f"--user-data-dir={user_data_dir}")
                options.add_argument(f"--profile-directory={profile_dir}")
            if headless.lower() == "true":
                options.add_argument("--headless")

            search = item

            driver = Chrome(options=options)
            web = "https://www.amazon.com/"
            driver.get(web)

            wait = WebDriverWait(driver, 20)

            search_xpath = '//input[@placeholder="Search Amazon" or @aria-label="Search"]'
            wait.until(EC.presence_of_element_located((By.XPATH, search_xpath)))
            search_box = driver.find_element(By.XPATH, search_xpath)
            search_box.send_keys(search + Keys.ENTER)

            title_lst = []
            price_lst = []
            asin_lst = []
            next_button_xpath = '//a[contains(@class, "s-pagination-next")]'
            for i in range(3):
                scrap_products(driver, wait, title_lst, price_lst, asin_lst)
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, next_button_xpath)))
                    next_button = driver.find_element(By.XPATH, next_button_xpath)
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

            upload_df_to_gsheet(df, sheet_name=search.replace(" ", "_")[:100])
        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    tic = time.time()
    main()
    toc = time.time()
    print(f"Program Running Time: {toc-tic} sec")