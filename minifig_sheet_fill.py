# Use bs4 and selenium to:
# 1. Log into my BrickLink account (super easy) (DONE: not as easy as I thought)
# 2. Navigate to 'My Collection' page (easy) (DONE: super easy)
# 3. Create a list of all item id's (e.g., njo0047) on all the pages of my collection (difficult)
# 4. Using id's, save name, ip, category (e.g., Rise of the Snakes), id, release date, condition, price*, quantity, and notes (moderate difficulty)
# 5. Scrape average used current price from each minifig page using previously written script (easy)
# 6. Save all information into a list (easy)
# 7. Possibly turn information into CSV (moderate difficulty)
# 8. Populate Goolge Sheets sheet with all the scraped information for a beautiful result (difficult)


# Do i make a function that grabs the price or do it while looping through collections??
# No matter what id have to open a new page for each price retrieval

# Left off on data collection of a single collection item
# Need to figure out how to collect info for every item per page

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

from dotenv import load_dotenv
import os

import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

load_dotenv()
user, passwd = os.getenv("UNAME"), os.getenv("PASSWD")

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

url = "https://store.bricklink.com/v2/login.page?menu=Home&logInTo=https%3A%2F%2Fstore.bricklink.com%2Fv2%2Fglobalcart.page"
driver.get(url)

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

soup = BeautifulSoup(driver.page_source, 'html.parser')

time.sleep(1)

list_item = soup.find(id='listItemView-1')

name = list_item.find('div', class_='text--bold l-cursor-pointer')
name = name.text.strip()

ip = list_item.find('div', class_='personal-inventory__item-category')
ip = ip.text.strip().split(':')[0].strip()

category = list_item.find('div', class_='personal-inventory__item-category')
category = category.text.strip().split(':')[1].strip()

identifier = list_item.find('div', class_='personal-inventory__list-item-list-cell--item-no text--break-word l-cursor-pointer')
identifier = identifier.text.strip()

condition = list_item.find('div', class_='personal-inventory__list-item-list-cell--cond')
condition = condition.text.strip()

qty_container = list_item.find('div', class_='personal-inventory__list-item-list-cell--qty')
if qty_container:
    input_tag = qty_container.find('input', class_='text-input text--center personal-inventory__list-qty')
    if input_tag and input_tag.has_attr('value'):
        quantity = input_tag['value']
    else:
        print("Input tag not found or missing value attribute.")
else:
    print("Quantity container not found.")

notes_div = list_item.find('div', class_='personal-inventory__cell--note l-margin-top--sm personal-inventory__note-field')
if notes_div:
    direct_text = notes_div.find(string=True, recursive=False)
    notes = direct_text.strip() if direct_text else "Add Notes"
else:
    notes = "No notes found"

print(f"{name}, {ip}, {category}, {identifier}, {condition}, {quantity}, {notes}")

time.sleep(10)

           
driver.quit()