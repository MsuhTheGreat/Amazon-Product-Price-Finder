from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
from time import sleep

load_dotenv()

CHROME_DATA_DIR = os.getenv("CHROME_DATA_DIR")
CHROME_PROFILE = os.getenv("CHROME_PROFILE", "Default")

options = ChromeOptions()
user_data_dir = rf"{CHROME_DATA_DIR}"
profile_dir = CHROME_PROFILE

if user_data_dir:
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
options.add_argument("--remote-debugging-port=9222")

search = "toy"

driver = Chrome(options=options)
web = "https://www.amazon.com/"
driver.get(web)

wait = WebDriverWait(driver, 5)

search_xpath = '//*[@id="twotabsearchtextbox"]'
wait.until(EC.presence_of_element_located((By.XPATH, search_xpath)))
search_box = driver.find_element(By.XPATH, search_xpath)
search_box.send_keys(search + Keys.ENTER)

sleep(5)

driver.quit()



