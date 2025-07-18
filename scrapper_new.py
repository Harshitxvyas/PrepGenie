import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def fetch_interview_links(company_to_filter, role_to_filter, pages_to_scrape):
    """
    Opens a browser, filters for company and role, and collects interview links.
    Returns a list of dictionaries, e.g., [{'title': '...', 'url': '...'}].
    """
    print("--- Step 1: Fetching interview links ---")
    target_url = "https://www.naukri.com/code360/interview-experiences"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)
    all_results = []

    try:
        driver.get(target_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "codingninjas-interview-experience-card-v2")))

        # --- Company Filter ---
        print(f"Filtering for company: {company_to_filter}...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-company-dropdown-widget > div"))).click()
        comp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search']")))
        comp_input.send_keys(company_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-radio-button.mat-radio-button"))).click()
        time.sleep(1)

        # --- Role Filter ---
        print(f"Filtering for role: {role_to_filter}...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-roles-dropdown-widget:nth-child(2) > div"))).click()
        role_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget input[placeholder='Search']")))
        role_input.send_keys(role_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget mat-checkbox"))).click()
        time.sleep(1)

        # --- Pagination and Link Collection ---
        for page in range(1, pages_to_scrape + 1):
            print(f"Collecting links from page {page}...")
            time.sleep(2)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.interview-experiences-list-section.ng-star-inserted")))
            cards = driver.find_elements(By.TAG_NAME, "codingninjas-interview-experience-card-v2")
            for card in cards:
                try:
                    anchor = card.find_element(By.CSS_SELECTOR, "a.interview-exp-title")
                    href = anchor.get_attribute("href")
                    text = anchor.text.strip()
                    if href and text:
                        all_results.append({"title": text, "url": href})
                except NoSuchElementException:
                    continue
            
            if page >= pages_to_scrape:
                break
            
            try:
                next_page_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//codingninjas-page-nav-v2//a[normalize-space(text())='{page + 1}']")))
                driver.execute_script("arguments[0].click();", next_page_link)
            except TimeoutException:
                print(f"Could not find link for page {page + 1}. Stopping link collection.")
                break
            
    except Exception as e:
        print(f"An error occurred while fetching links: {e}")
    finally:
        driver.quit()
        print(f"Found {len(all_results)} links to scrape.")
        return all_results

def scrape_interview_details(url):
    """
    Scrapes BOTH the overall journey and the detailed, numbered rounds from a single URL.
    """
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--log-level=3')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        driver.get(url)
        time.sleep(7)

        description_parts = []
        # Selectors
        JOURNEY_SELECTOR = "#ie-overall-user-experience"
        CONTINUE_READING_BUTTON_SELECTOR = "#continue-reading-ie-cta-container button"
        ROUND_CONTAINER_BASE_ID = "interview-round-v2-"
        
        # --- Scrape Journey ---
        try:
            try:
                continue_button = driver.find_element(By.CSS_SELECTOR, CONTINUE_READING_BUTTON_SELECTOR)
                driver.execute_script("arguments[0].click();", continue_button)
                time.sleep(1)
            except NoSuchElementException:
                pass
            journey_element = driver.find_element(By.CSS_SELECTOR, JOURNEY_SELECTOR)
            description_parts.append("## Interview Preparation Journey\n" + journey_element.text.strip())
        except NoSuchElementException:
            pass

        # --- Scrape Rounds ---
        round_index = 1
        found_rounds = False
        while True:
            try:
                round_id = f"{ROUND_CONTAINER_BASE_ID}{round_index}"
                round_container = driver.find_element(By.ID, round_id)
                if not found_rounds:
                    description_parts.append("\n\n## Interview Rounds")
                    found_rounds = True
                description_parts.append(f"\n\n### Round {round_index}\n" + round_container.text.strip())
                round_index += 1
            except NoSuchElementException:
                break
        
        if not description_parts:
            # Fallback for pages with a different structure
            try:
                fallback_selector = "div.blog-body-content"
                content_element = driver.find_element(By.CSS_SELECTOR, fallback_selector)
                if content_element.text.strip():
                    description_parts.append(content_element.text.strip())
            except NoSuchElementException:
                 return None

        return "\n".join(description_parts)
    except Exception as e:
        print(f"    -> An error occurred while scraping details from {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def main():
    """
    Main function to get user input, fetch links, scrape details, and return a DataFrame.
    """
    # --- Get User Input ---
    company_to_filter = input("Enter the company name to search for: ").strip()
    role_to_filter_input = input("Enter the role name (e.g., SDE 1, SDE-2): ").strip()
    
    # Normalize role input for better matching
    role_to_filter = re.sub(r'\s*-\s*', ' - ', role_to_filter_input)
    role_to_filter = " ".join(role_to_filter.split()).upper()

    try:
        pages_to_scrape = int(input("How many pages of results do you want to scrape? "))
    except ValueError:
        print("Invalid number. Defaulting to 1 page.")
        pages_to_scrape = 1

    # --- Step 1: Fetch all the links first ---
    links_to_process = fetch_interview_links(company_to_filter, role_to_filter, pages_to_scrape)

    if not links_to_process:
        print("No interview links found for the given criteria. Exiting.")
        return None # Return None if no links were found

    # --- Step 2: Scrape the details from each link ---
    print("\n--- Step 2: Scraping details from each link ---")
    scraped_data = []
    total_links = len(links_to_process)
    for i, item in enumerate(links_to_process):
        url = item.get('URL') or item.get('url')
        title = item.get('Title') or item.get('title')
        
        print(f"Scraping link {i + 1}/{total_links}: {title}...")
        description = scrape_interview_details(url)

        if description:
            try:
                parts = [part.strip() for part in title.split('|')]
                company = parts[0]
                role = parts[1]
            except (IndexError, AttributeError):
                company = company_to_filter
                role = role_to_filter_input
            
            scraped_data.append({"company": company, "role": role, "description": description})
            print(f"  -> Success.")
        else:
            print(f"  -> Failed to retrieve data.")

    # --- Step 3: Create and return the pandas DataFrame ---
    if scraped_data:
        print("\n✅ All done! Creating final pandas DataFrame.")
        # Create the DataFrame from the collected data
        output_df = pd.DataFrame(scraped_data)
        # Return the DataFrame so it can be used by other parts of your application
        return output_df
    else:
        print("\nNo data was successfully scraped.")
        return None

if __name__ == "__main__":
    # The main() function is called, and its return value (the DataFrame) is stored
    final_dataframe = main()
    
    # Check if the DataFrame was created successfully and print it
    if final_dataframe is not None:
        print("\n--- Final DataFrame ---")
        print(final_dataframe)