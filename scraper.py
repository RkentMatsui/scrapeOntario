from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import csv
import time

# --- Setup Selenium Webdriver ---
chrome_options = Options()
# Comment the next line to run in headless mode (without a visible browser window)
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

URL = "https://www.ontariosignassociation.com/member-directory"
driver.get(URL)

all_profile_links = []
scrapedData = []

print("--- Phase 1: Gathering all member profile links ---")

try:
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#idPagingData select option'))
    )
    
    num_options = len(driver.find_elements(By.CSS_SELECTOR, '#idPagingData select option'))
    print(f"Found {num_options} pages to scrape.")

    for i in range(num_options):
        print(f"Scanning page {i + 1}/{num_options} for links...")
        
        page_select_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#idPagingData select'))
        )
        page_select_element.click()
        driver.find_element(By.CSS_SELECTOR, f'#idPagingData select option:nth-child({i + 1})').click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#membersTable .memberDirectoryColumn1 a'))
        )
        
        link_elements = driver.find_elements(By.CSS_SELECTOR, '#membersTable .memberDirectoryColumn1 a')
        for link_element in link_elements:
            href = link_element.get_attribute('href')
            if href:
                all_profile_links.append(href)

except TimeoutException as e:
    print(f"A timeout occurred during link gathering: {e}")
except Exception as e:
    print(f"An error occurred during link gathering: {e}")

print(f"\n--- Phase 1 Complete: Found {len(all_profile_links)} total profiles ---\n")


print("--- Phase 2: Scraping details from each profile page ---")
for idx, profile_url in enumerate(all_profile_links):
    try:
        print(f"Scraping ({idx + 1}/{len(all_profile_links)}): {profile_url}")
        driver.get(profile_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'fieldContainer'))
        )
        
        profile_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Initialize dictionary with all keys
        data_dict = { 'Company Name': '', 'Contact Name': '', 'Phone': '', 'Email': '', 'Website': '', 'Address': '', 'City': '', 'Province/State': '' }

        # Loop through all fields to find the data
        for container in profile_soup.find_all('div', class_='fieldContainer simpleTextContainer'):
            label_elem = container.find(['div', 'span'], class_='fieldLabel')
            value_elem = container.find(['div', 'span'], class_='fieldBody')
            
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True).lower().replace(':', '')
                
                # Special handling for email link
                if 'email' in label:
                    email_tag = value_elem.find('a')
                    data_dict['Email'] = email_tag.get_text(strip=True) if email_tag else ''
                # Handle all other fields as plain text
                else:
                    value = value_elem.get_text(separator=' ', strip=True)
                    
                    if 'company' in label:
                        data_dict['Company Name'] = value
                    elif 'web site' in label:
                        data_dict['Website'] = value
                    elif 'first name' in label:
                        data_dict['Contact Name'] = value
                    elif 'last name' in label:
                        data_dict['Contact Name'] = data_dict.get('Contact Name', '') + " " + value
                    elif 'phone' in label:
                        data_dict['Phone'] = value
                    elif 'address' in label:
                        data_dict['Address'] = value
                    elif 'city' in label:
                        data_dict['City'] = value
                    elif 'province' in label or 'state' in label:
                        data_dict['Province/State'] = value
        
        print(f"  -> Found: {data_dict.get('Company Name', 'Name Not Found')}")
        scrapedData.append(data_dict)

    except TimeoutException:
        print(f"  - Timeout while loading profile: {profile_url}")
    except Exception as e:
        print(f"  - Could not scrape profile {profile_url}. Error: {e}")


# --- Cleanup and Save ---
driver.quit()

with open('ontario_sign_detailed_profiles.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Company Name', 'Contact Name', 'Phone', 'Email', 'Website', 'Address', 'City', 'Province/State']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(scrapedData)

print(f"\n--- Scraping Complete: {len(scrapedData)} records saved to ontario_sign_detailed_profiles.csv ---")