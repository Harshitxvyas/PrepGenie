import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed

# ✅ Chromium-compatible headless driver
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import shutil

def get_chrome_driver():
    # ✅ Automatically install compatible driver
    chromedriver_autoinstaller.install()

    chrome_options = Options()
    chrome_path = shutil.which("chromium")  # dynamically resolve path
    chrome_options.binary_location = chrome_path
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    return webdriver.Chrome(options=chrome_options)

# ✅ Scrape interview links
def fetch_interview_links(company: str, role: str, pages: int = 1):
    base_url = "https://www.codingninjas.com/studio/experiences"
    search_url = f"{base_url}?company={company}&title={role}"
    
    driver = get_chrome_driver()
    driver.get(search_url)
    time.sleep(2)

    links = set()
    for _ in range(pages):
        try:
            elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/experiences/")]')
            for el in elements:
                href = el.get_attribute("href")
                if href and "/experiences/" in href:
                    links.add(href)
            # Click next if exists
            next_button = driver.find_element(By.XPATH, '//button[contains(text(), "Next")]')
            if next_button.is_enabled():
                next_button.click()
                time.sleep(2)
            else:
                break
        except Exception as e:
            print(f"Error during pagination: {e}")
            break

    driver.quit()
    return list(links)

# ✅ Extract data from one interview URL
def parse_interview_page(url):
    driver = get_chrome_driver()
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)

        title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
        role = driver.find_element(By.CSS_SELECTOR, "span.round-badge").text

        description = driver.find_element(By.CSS_SELECTOR, 'div[class*="experience-details"]').text

        return {
            "url": url,
            "title": title.strip(),
            "role": role.strip(),
            "description": description.strip()
        }

    except (NoSuchElementException, TimeoutException) as e:
        print(f"Error scraping {url}: {e}")
        return None
    finally:
        driver.quit()

# ✅ Threaded scraping of all links
def fetch_all_interviews(company, role, pages=1, max_threads=5):
    links = fetch_interview_links(company, role, pages)
    print(f"Found {len(links)} links")

    data = []
    with ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {executor.submit(parse_interview_page, url): url for url in links}
        for future in as_completed(future_to_url):
            result = future.result()
            if result:
                data.append(result)

    return pd.DataFrame(data)


