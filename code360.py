import pandas as pd
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# ✅ Correct Chrome Driver Setup for Streamlit/Cloud
def get_streamlit_chrome_driver():
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"  # ⬅️ Correct path for Streamlit Cloud
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# ✅ Step 1: Fetch interview links
def fetch_interview_links(company_to_filter, role_to_filter, pages_to_scrape):
    print("--- Step 1: Fetching interview links ---")
    url = "https://www.naukri.com/code360/interview-experiences"
    driver = get_streamlit_chrome_driver()
    wait = WebDriverWait(driver, 15)
    all_results = []

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "codingninjas-interview-experience-card-v2")))

        # Company filter
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-company-dropdown-widget > div"))).click()
        comp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search']")))
        comp_input.send_keys(company_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-radio-button.mat-radio-button"))).click()
        time.sleep(1)

        # Role filter
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-roles-dropdown-widget:nth-child(2) > div"))).click()
        role_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget input[placeholder='Search']")))
        role_input.send_keys(role_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget mat-checkbox"))).click()
        time.sleep(1)

        # Loop pages
        for page in range(1, pages_to_scrape + 1):
            print(f"Collecting links from page {page}...")
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

            if page < pages_to_scrape:
                try:
                    next_page = wait.until(EC.element_to_be_clickable((By.XPATH, f"//codingninjas-page-nav-v2//a[normalize-space(text())='{page + 1}']")))
                    driver.execute_script("arguments[0].click();", next_page)
                    time.sleep(2)
                except TimeoutException:
                    print(f"Page {page + 1} not found.")
                    break

    except Exception as e:
        print(f"Error in fetch_interview_links: {e}")
    finally:
        driver.quit()
        print(f"✅ Found {len(all_results)} links.")
        return all_results


# ✅ Step 2: Scrape individual page
def scrape_interview_details(url):
    driver = None
    try:
        driver = get_streamlit_chrome_driver()
        driver.get(url)
        time.sleep(5)

        parts = []

        # Expand journey
        try:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "#continue-reading-ie-cta-container button")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
            except:
                pass

            journey = driver.find_element(By.CSS_SELECTOR, "#ie-overall-user-experience").text.strip()
            if journey:
                parts.append("## Interview Preparation Journey\n" + journey)
        except NoSuchElementException:
            pass

        # Rounds
        round_index = 1
        rounds_found = False
        while True:
            try:
                round_id = f"interview-round-v2-{round_index}"
                round_container = driver.find_element(By.ID, round_id)
                round_text = round_container.text.strip()

                if not rounds_found:
                    parts.append("\n\n## Interview Rounds")
                    rounds_found = True

                parts.append(f"\n\n### Round {round_index}\n{round_text}")
                round_index += 1
            except NoSuchElementException:
                break

        # Fallback
        if not parts:
            try:
                fallback = driver.find_element(By.CSS_SELECTOR, "div.blog-body-content").text.strip()
                if fallback:
                    parts.append(fallback)
            except:
                return None

        return "\n".join(parts)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


# ✅ Step 3: Wrap for threads
def scrape_link_wrapper(item, company, role):
    url = item.get("url") or item.get("URL")
    title = item.get("title") or item.get("Title")
    description = scrape_interview_details(url)

    if description:
        try:
            c, r = [part.strip() for part in title.split("|")]
        except:
            c, r = company, role
        return {"company": c, "role": r, "description": description}
    return None


# ✅ Step 4: Main function to get df
def fetch_interview_data(company, role_input, pages):
    role = re.sub(r'\s*-\s*', ' - ', role_input).upper()
    pages = max(1, int(pages))

    links = fetch_interview_links(company, role, pages)
    if not links:
        print("❌ No links found.")
        return None

    print("--- Scraping interview details ---")
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(scrape_link_wrapper, item, company, role_input): item
            for item in links
        }
        for i, f in enumerate(as_completed(futures), 1):
            res = f.result()
            print(f"Scraped {i}/{len(links)}")
            if res:
                results.append(res)

    if results:
        print("✅ Done.")
        return pd.DataFrame(results)
    else:
        print("❌ Nothing scraped.")
        return None
