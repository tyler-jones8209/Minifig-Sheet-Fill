# Use bs4 and selenium to:
# 1. Log into my BrickLink account (super easy) (DONE: not as easy as I thought)
# 2. Navigate to 'My Collection' page (easy) (DONE: super easy)
# 3. Create a list of all item id's (e.g. njo0047) on all the pages of my collection (difficult)
# 4. Using id's, save name, id, release date, price*, quantity, and notes (moderate difficulty)
# 5. Scrape average used current price from each minifig page using previously written script (easy)
# 6. Save all information into a list (easy)
# 7. Possibly turn information into CSV (moderate difficulty)
# 8. Populate Goolge Sheets sheet with all the scraped information for a beautiful result (difficult)


# Left off on successfully getting past the login screen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from dotenv import load_dotenv
import os

import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

load_dotenv()
user, passwd = os.getenv("UNAME"), os.getenv("PASSWD")

options = webdriver.ChromeOptions()
#options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

url = "https://store.bricklink.com/v2/login.page?menu=Home&logInTo=https%3A%2F%2Fstore.bricklink.com%2Fv2%2Fglobalcart.page"
driver.get(url)

soup = BeautifulSoup(driver.page_source, 'html.parser')

try:
    cookie_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//button[text()='Just necessary']"))
    )
    driver.execute_script("arguments[0].click();", cookie_btn)
    print("Cookie banner dismissed via JS.")
except Exception as e:
    print("Cookie notice not dismissed:", e)


username_field = driver.find_element(By.ID, 'frmUsername')
password_field = driver.find_element(By.ID, 'frmPassword')
driver.find_element(By.ID, 'blbtnLogin')
username_field.send_keys(user)
password_field.send_keys(passwd)

driver.find_element(By.ID, 'blbtnLogin').click()

time.sleep(1)

driver.get("https://www.bricklink.com/v3/myCollection/main.page?q=&itemType=M&page=1")

time.sleep(10)

           
driver.quit()