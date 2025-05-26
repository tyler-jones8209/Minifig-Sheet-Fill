# Use bs4 and selenium to:
# 1. Log into my BrickLink account (super easy) (DONE: not as easy as I thought)
# 2. Navigate to 'My Collection' page (easy) (DONE: super easy)
# 3. Create a list of all item id's (e.g., njo0047) on all the pages of my collection (difficult) (DONE: more or less)
# 4. Using id's, save name, theme, subtheme (e.g., Rise of the Snakes), id, release date, condition, price*, quantity, and notes (moderate difficulty) (DONE)
# 5. Scrape average used current price from each minifig page using previously written script (easy) (DONE: need to update it to get price based on condition)
# 6. Save all information into a list (easy) (DONE)
# 7. Possibly turn information into CSV (moderate difficulty) (DONE: not gonna use it for the google sheet but still cool to have)
# 8. Populate Goolge Sheets sheet with all the scraped information for a beautiful result (difficult) (DONE: actually was easy since I had stuff set up already)

# Sister scripts I could make:
# 1. Another Google Sheets filler that populates a sheet with name, item number, and every price listed in the Price Guide. 
#       This would include min, avg, and max prices for new and used during the last 6 months and new and used during the current period (12 total prices)
#       I'm pretty sure I can pull this info in any other sheet I make just using '=SOME_FUNCTION(item_number)' which could be useful
# 2. A script similar to this one, except it gets info from a specified list in 'My Wanted Lists' 
#       I would include name, item number, theme, subtheme, price, checkbox for if acquired
#       Not sure what utility this would have other than BrickLink's wishlists are UGLY 

# html parsing and browser surfing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

# using .env 
from dotenv import load_dotenv
import os

# time
import time

# Google Sheets and CSV handling
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

def login(driver, username, password):
    # load login page
    url = "https://store.bricklink.com/v2/login.page?menu=Home&logInTo=https%3A%2F%2Fstore.bricklink.com%2Fv2%2Fglobalcart.page"
    driver.get(url)

    # wait for cookie popup and destroy that shit (using JS because it didn't work the other way)
    cookie_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//button[text()='Just necessary']"))
    )
    driver.execute_script("arguments[0].click();", cookie_btn)

    # fill username and password fields
    username_field = driver.find_element(By.ID, 'frmUsername')
    password_field = driver.find_element(By.ID, 'frmPassword')
    driver.find_element(By.ID, 'blbtnLogin')
    username_field.send_keys(username)
    password_field.send_keys(password)

    # click login button
    driver.find_element(By.ID, 'blbtnLogin').click()

def get_total_pages(driver):
    # load the first My Collection page initially to retrieve number of total pages
    driver.get("https://www.bricklink.com/v3/myCollection/main.page?q=&itemType=M&page=1")
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    time.sleep(0.5)

    # scrape total number of pages for looping
    pagination_jump = soup.find('label', class_='pagination__jump')

    # setting page_amount to 1 as a default means if the pagination jump is missing, it only page one gets added to the list of pages to scrape
    page_amount = 1

    page_numbers = []
    if pagination_jump:
        pagination_jump = pagination_jump.text.strip()
        page_amount = int(pagination_jump.split('/')[1].strip())
    for x in range(1, page_amount + 1):
        page_numbers.append(x)

    return page_numbers

# function to scrape price (based on listed condition) and release year from minifig specific pages
def scrape_release_and_price(driver, identifier, condition):

    # load "Price Guide" page using the minifigs item number
    driver.get(f"https://www.bricklink.com/v2/catalog/catalogitem.page?M={identifier}#T=P")

    # halt program until presence of price tables is detected, otherwise set variables as empty
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'pcipgSummaryTable'))
        )
    except Exception as e:
        print(f"Timed out waiting for tables on {identifier}: {e}")
        return "", ""

    # get page data
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # scrape price
    # store tables with class the class 'pcipgSummaryTable' (since all tables share the same class)
    tables = soup.find_all('table', class_='pcipgSummaryTable')
    if len(tables) < 4:
        print(f"Expected at least 4 tables for identifier {identifier}, but found {len(tables)}")
        price = ""
    else:
        # choose which table based on condition
        if str(condition).lower() == 'used':
            table = tables[3]
        elif str(condition).lower() == 'new':
            table = tables[2]
        # get all the rows from selected table
        rows = table.find('tbody').find_all('tr')
        if len(rows) > 3:
            price_cell = rows[3].find_all('td')[1]
            price_text = price_cell.text.strip()
            try:
                price = f"{float(price_text.split('$')[1]):.2f}"
            except (IndexError, ValueError):
                price = ""
        else:
            price = ""

    # scrape release year
    year_element = soup.find(id='yearReleasedSec')
    release_year = year_element.text.strip()
    if year_element is None:
        release_year = ""

    return price, release_year

def scrape_minifig_info(driver, page_numbers):
    # this houses all of the scraped info; each item is a list
    minifig_info = []

    # loop through all pages containing minifigs in My Collection
    for page in page_numbers:
        driver.get(f"https://www.bricklink.com/v3/myCollection/main.page?q=&itemType=M&page={str(page)}")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'listItemView-0'))
        )  

        # get data for each visited page
        minifig_soup = BeautifulSoup(driver.page_source, 'html.parser')  

        # get any data under elements that contain the id listItemView-XX (e.g., listItemView-0, listItemView-23)
        list_items = minifig_soup.find_all(id=re.compile('^listItemView-\d+$'))
        for item in list_items:
            item_id = item.get_attribute_list('id')

            # get data for each listViewItem-XX id
            list_item = minifig_soup.find(id=str(item_id[0]))

            # scrape minifig name
            name = list_item.find('div', class_='text--bold l-cursor-pointer')
            name = name.text.strip()
            if name is None:
                name = ""

            # scrape theme of minifig (e.g., Ninjago, Indiana Jones, etc)
            # scrape subtheme of theme (e.g., NINJAGO: Rise of the Snakes, Star Wars: Star Wars Episode 1, Super Heroes: Batman II)
            theme_text = list_item.find('div', class_='personal-inventory__item-category')
            theme_text = theme_text.text.strip()
            parts   = [p.strip() for p in theme_text.split(':', 1)]
            if len(parts) == 1:
                theme, subtheme = parts[0], "N/A"
            else:
                theme, subtheme = parts[0], parts[1]

            # scrape BrickLink item number (e.g., njo0047, sw0002, sh0041)
            identifier = list_item.find('div', class_='personal-inventory__list-item-list-cell--item-no text--break-word l-cursor-pointer')
            identifier = identifier.text.strip()
            if identifier is None:
                identifier = ""

            # scrape chosen condition of minifig (used or new)
            condition = list_item.find('div', class_='personal-inventory__list-item-list-cell--cond')
            condition = condition.text.strip()
            if condition is None:
                condition = ""

            # scrape price and release year from a different page using a function
            price, release_year = scrape_release_and_price(driver, identifier, condition)
            if price is None:
                price = ""
            if release_year is None:
                release_year = ""

            # scrape quantity of minifigs in collection
            qty_container = list_item.find('div', class_='personal-inventory__list-item-list-cell--qty')
            if qty_container:
                input_tag = qty_container.find('input', class_='text-input text--center personal-inventory__list-qty')
                if input_tag and input_tag.has_attr('value'):
                    quantity = input_tag['value']
                else:
                    print("Input tag not found or missing value attribute.")
                    quantity = ""
            else:
                print("Quantity container not found.")
                quantity = ""

            # scrape and transfer over any added notes
            notes_div = list_item.find('div', class_='personal-inventory__cell--note l-margin-top--sm personal-inventory__note-field')
            if notes_div:
                direct_text = notes_div.find(string=True, recursive=False)
                if direct_text:
                    notes = direct_text.strip()
                else:
                    notes = ""
            else:
                notes = "Error parsing notes."

            minifig_info.append([name, identifier, theme, subtheme, release_year, condition, price, quantity, notes])

    return minifig_info

def write_to_csv(minifig_info):
    with open('scraped_minifig_info.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'id', 'theme', 'subtheme', 'release', 'condition', 'price', 'quantity', 'notes'])
        writer.writerows(minifig_info)

# function to populate a chosen google sheet
# need to really go through and relearn this code; I just copied it from a older project I made
# also need to relearn how the credentials work so I can add it in the github documentation
def fill_google_sheet(minifig_info):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('c:/Users/tdjon/Projects/BrickLink/Minifig_Sheet_Fill/logical-veld-439501-v7-8119ef621faf.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open("Minifigure Collection").sheet1

    range_to_clear = "A2:I1000"

    sheet.batch_clear([range_to_clear])

    start_row = 2

    cell_range = f'A{start_row}:I{start_row + len(minifig_info) - 1}'
    cell_list = sheet.range(cell_range)

    flat_data = [item for sublist in minifig_info for item in sublist]

    for i, cell in enumerate(cell_list):
        cell.value = flat_data[i]

    sheet.update_cells(cell_list)

def main():
    start = time.perf_counter()

    # select web driver and set to 'headless' so it doesn't display while it runs (though it is super sick to see when not headless)
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    # load data stored in .env file
    load_dotenv()
    user, passwd = os.getenv("UNAME"), os.getenv("PASSWD")

    login(driver=driver, username=user, password=passwd)

    time.sleep(0.5)
    
    page_numbers = get_total_pages(driver=driver)

    minifig_info = scrape_minifig_info(driver=driver, page_numbers=page_numbers)

    time.sleep(10)
            
    driver.quit()

    # works but need to fix it so that names with inner quotes don't keep the added outer quotes
    #write_to_csv(minifig_info)

    # populate google sheet
    fill_google_sheet(minifig_info)

    end = time.perf_counter()

    # need to figure out if I can reduce runtime
    # runs on my collection (65 entries) took: run1: 68.67s, run2: 78.40s, run3: 77.50s, run4: 75.12s, run5: 72.91s
    print(f"Runtime: {end - start}s")

if __name__ == '__main__':
    main()