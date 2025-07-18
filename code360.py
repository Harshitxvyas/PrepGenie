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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import shutil
import os


import os
import subprocess
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

CHROMEDRIVER_PATH = "/tmp/chromedriver"
CHROME_BINARY = shutil.which("chromium")  # Streamlit Cloud uses `chromium`

# Avoid Streamlit file watcher error
os.environ["STREAMLIT_DISABLE_WATCHDOG_WARNINGS"] = "true"
os.environ["STREAMLIT_WATCH_MODE"] = "poll"

def download_chromedriver():
    url = "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.224/linux64/chromedriver-linux64.zip"
    zip_path = "/tmp/chromedriver.zip"
    extract_path = "/tmp/chromedriver-linux64"

    subprocess.run(["wget", url, "-O", zip_path], check=True)
    subprocess.run(["unzip", "-o", zip_path, "-d", "/tmp/"], check=True)
    final_path = os.path.join(extract_path, "chromedriver")
    subprocess.run(["chmod", "+x", final_path], check=True)
    shutil.copy(final_path, CHROMEDRIVER_PATH)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.binary_location = "/usr/bin/chromium"  # For Streamlit Cloud

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

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


