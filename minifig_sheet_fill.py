# Use bs4 and selenium to:
# 1. Log into my BrickLink account (super easy) (DONE: not as easy as I thought)
# 2. Navigate to 'My Collection' page (easy) (DONE: super easy)
# 3. Create a list of all item id's (e.g., njo0047) on all the pages of my collection (difficult) (DONE: more or less)
# 4. Using id's, save name, ip, category (e.g., Rise of the Snakes), id, release date, condition, price*, quantity, and notes (moderate difficulty) (DONE)
# 5. Scrape average used current price from each minifig page using previously written script (easy) (DONE: need to update it to get price based on condition)
# 6. Save all information into a list (easy) (DONE)
# 7. Possibly turn information into CSV (moderate difficulty)
# 8. Populate Goolge Sheets sheet with all the scraped information for a beautiful result (difficult)

# Left off on being able to collect data for every minifig on every page (theoreticaly)
# Before i move on to turning into a CSV or trying to populate a sheet, I need to clean up the code cause it's MESSY AF
# Maybe also go throuhg and see what I can turn into functions and setting failsafes for variables

# On My Collection page, there is a box that lets you pick what page to go to
# Luckily, that portion includes the total amount of pages "'jump to:'____ / <last_page_number>"

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


# function to scrape price and release year from minifig specific pages
# NEED to update it to pick the price based on condition
# currently it defaults to the avg used current price
def scrape_release_and_price(driver, identifier, condition):
    driver.get(f"https://www.bricklink.com/v2/catalog/catalogitem.page?M={identifier}#T=P")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'pcipgSummaryTable'))
        )
    except Exception as e:
        print(f"Timed out waiting for tables on {identifier}: {e}")
        return "N/A", "N/A"

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # scrape price
    tables = soup.find_all('table', class_='pcipgSummaryTable')
    if len(tables) < 4:
        print(f"Expected at least 4 tables for identifier {identifier}, but found {len(tables)}")
        price = "N/A"
    else:
        if str(condition).lower() == 'used':
            table = tables[3]
        elif str(condition).lower() == 'new':
            table = tables[2]
        rows = table.find('tbody').find_all('tr')
        if len(rows) > 3:
            price_cell = rows[3].find_all('td')[1]
            price_text = price_cell.text.strip()
            try:
                price = f"{float(price_text.split('$')[1]):.2f}"
            except (IndexError, ValueError):
                price = "N/A"
        else:
            price = "N/A"

    # scrape release year
    year_elem = soup.find(id='yearReleasedSec')
    release_year = year_elem.text.strip() if year_elem else "N/A"

    return price, release_year


load_dotenv()
user, passwd = os.getenv("UNAME"), os.getenv("PASSWD")

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

url = "https://store.bricklink.com/v2/login.page?menu=Home&logInTo=https%3A%2F%2Fstore.bricklink.com%2Fv2%2Fglobalcart.page"
driver.get(url)


cookie_btn = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//button[text()='Just necessary']"))
)
driver.execute_script("arguments[0].click();", cookie_btn)

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

# scrape total number of pages for looping
pagination_jump = soup.find('label', class_='pagination__jump')
page_amount = 1

page_numbers = []

if pagination_jump:
    pagination_jump = pagination_jump.text.strip()
    page_amount = int(pagination_jump.split('/')[1].strip())

for x in range(1, page_amount + 1):
    page_numbers.append(x)

minifig_info = []

for page in page_numbers:
    driver.get(f"https://www.bricklink.com/v3/myCollection/main.page?q=&itemType=M&page={str(page)}")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'listItemView-0'))
    )  

    minifig_soup = BeautifulSoup(driver.page_source, 'html.parser')  

    list_items = minifig_soup.find_all(id=re.compile('^listItemView-\d+$'))
    for item in list_items:
        item_id = item.get_attribute_list('id')
        list_item = minifig_soup.find(id=str(item_id[0]))

        # scrape minifig name
        name = list_item.find('div', class_='text--bold l-cursor-pointer')
        name = name.text.strip()

        # scrape intellectual property minifig (e.g., Ninjago, Indiana Jones, etc)
        # scrape subcategory of IP (e.g., NINJAGO: Rise of the Snakes, Star Wars: Star Wars Episode 1, Super Heroes: Batman II)
        ip_text = list_item.find('div', class_='personal-inventory__item-category')
        ip_text = ip_text.text.strip()
        parts   = [p.strip() for p in ip_text.split(':', 1)]
        if len(parts) == 1:
            ip, category = parts[0], ""
        else:
            ip, category = parts[0], parts[1]

        # scrape BrickLink item number (e.g., njo0047, sw0002, sh0041)
        identifier = list_item.find('div', class_='personal-inventory__list-item-list-cell--item-no text--break-word l-cursor-pointer')
        identifier = identifier.text.strip()

        # scrape chosen condition of minifig (used or new)
        condition = list_item.find('div', class_='personal-inventory__list-item-list-cell--cond')
        condition = condition.text.strip()

        # scrape price and release year from a different page using a function
        price, release_year = scrape_release_and_price(driver, identifier, condition)

        # scrape quantity of minifigs in collection
        qty_container = list_item.find('div', class_='personal-inventory__list-item-list-cell--qty')
        if qty_container:
            input_tag = qty_container.find('input', class_='text-input text--center personal-inventory__list-qty')
            if input_tag and input_tag.has_attr('value'):
                quantity = input_tag['value']
            else:
                print("Input tag not found or missing value attribute.")
        else:
            print("Quantity container not found.")

        # scrape and transfer over any added notes
        notes_div = list_item.find('div', class_='personal-inventory__cell--note l-margin-top--sm personal-inventory__note-field')
        if notes_div:
            direct_text = notes_div.find(string=True, recursive=False)
            notes = direct_text.strip() if direct_text else "Add Notes"
        else:
            notes = "No notes found"

        minifig_info.append([name, identifier, ip, category, release_year, condition, price, quantity, notes])

time.sleep(10)
           
driver.quit()