import pandas as pd
import re
import time
import os
import shutil
import subprocess
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed

# Environment setup
os.environ["STREAMLIT_DISABLE_WATCHDOG_WARNINGS"] = "true"
os.environ["STREAMLIT_WATCH_MODE"] = "poll"

def find_chrome_binary():
    """Find Chrome/Chromium binary across different systems"""
    possible_paths = [
        # Windows
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        
        # Linux - common locations
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        "/usr/local/bin/chrome",
        "/usr/local/bin/chromium",
        
        # Flatpak
        "/var/lib/flatpak/app/com.google.Chrome/current/active/export/bin/com.google.Chrome",
        
        # AppImage or other custom locations
        "/opt/google/chrome/chrome",
        "/opt/chromium/chromium"
    ]
    
    # First try using 'which' command
    try:
        for binary_name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
            result = shutil.which(binary_name)
            if result:
                print(f"Found Chrome binary via which: {result}")
                return result
    except Exception as e:
        print(f"Error using which command: {e}")
    
    # Then check predefined paths
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found Chrome binary at: {path}")
            return path
    
    # Try to find using whereis (Linux)
    try:
        if platform.system() == "Linux":
            result = subprocess.run(["whereis", "chrome"], capture_output=True, text=True)
            if result.returncode == 0:
                paths = result.stdout.strip().split()[1:]  # Skip the first element (command name)
                for path in paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        print(f"Found Chrome binary via whereis: {path}")
                        return path
    except Exception as e:
        print(f"Error using whereis: {e}")
    
    return None

def install_chrome_if_needed():
    """Install Chrome if not found (Linux only)"""
    if platform.system() != "Linux":
        return False
    
    try:
        print("Attempting to install Chrome...")
        # Update package list
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        
        # Install Chrome
        subprocess.run([
            "sudo", "apt-get", "install", "-y", 
            "wget", "gnupg", "software-properties-common"
        ], check=True)
        
        # Add Google's signing key
        subprocess.run([
            "wget", "-q", "-O", "-", 
            "https://dl.google.com/linux/linux_signing_key.pub"
        ], stdout=subprocess.PIPE, check=True)
        
        # Add Chrome repository
        subprocess.run([
            "sudo", "sh", "-c", 
            "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' >> /etc/apt/sources.list.d/google-chrome.list"
        ], check=True)
        
        # Update and install
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "google-chrome-stable"], check=True)
        
        return True
    except Exception as e:
        print(f"Failed to install Chrome: {e}")
        return False

def get_chrome_driver():
    """Get Chrome driver with automatic binary detection"""
    chrome_options = Options()
    
    # Essential options for headless operation
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Find Chrome binary
    chrome_binary = find_chrome_binary()
    
    if not chrome_binary:
        print("Chrome binary not found. Trying to install...")
        if install_chrome_if_needed():
            chrome_binary = find_chrome_binary()
        
        if not chrome_binary:
            raise Exception(
                "Chrome/Chromium not found. Please install Chrome or Chromium:\n"
                "Ubuntu/Debian: sudo apt-get install google-chrome-stable\n"
                "CentOS/RHEL: sudo yum install google-chrome-stable\n"
                "Windows: Download from https://www.google.com/chrome/\n"
                "macOS: Download from https://www.google.com/chrome/"
            )
    
    chrome_options.binary_location = chrome_binary
    print(f"Using Chrome binary: {chrome_binary}")
    
    try:
        # Use ChromeDriverManager for automatic driver management
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error creating driver with ChromeDriverManager: {e}")
        
        # Fallback: try without ChromeDriverManager
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e2:
            print(f"Error creating driver without ChromeDriverManager: {e2}")
            raise e2

def test_driver():
    """Test if the driver works correctly"""
    try:
        driver = get_chrome_driver()
        driver.get("https://www.google.com")
        print("Driver test successful!")
        driver.quit()
        return True
    except Exception as e:
        print(f"Driver test failed: {e}")
        return False

# ✅ Scrape interview links
def fetch_interview_links(company: str, role: str, pages: int = 1):
    base_url = "https://www.codingninjas.com/studio/experiences"
    search_url = f"{base_url}?company={company}&title={role}"
    
    driver = get_chrome_driver()
    try:
        driver.get(search_url)
        time.sleep(3)  # Increased wait time

        links = set()
        for page in range(pages):
            try:
                print(f"Scraping page {page + 1}")
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/experiences/")]')
                page_links = 0
                for el in elements:
                    href = el.get_attribute("href")
                    if href and "/experiences/" in href:
                        links.add(href)
                        page_links += 1
                
                print(f"Found {page_links} links on page {page + 1}")
                
                # Try to go to next page
                if page < pages - 1:
                    try:
                        next_button = driver.find_element(By.XPATH, '//button[contains(text(), "Next")]')
                        if next_button.is_enabled():
                            next_button.click()
                            time.sleep(3)
                        else:
                            print("Next button disabled, stopping pagination")
                            break
                    except NoSuchElementException:
                        print("No next button found, stopping pagination")
                        break
                        
            except Exception as e:
                print(f"Error during pagination on page {page + 1}: {e}")
                break

        return list(links)
        
    finally:
        driver.quit()

# ✅ Extract data from one interview URL
def parse_interview_page(url):
    driver = get_chrome_driver()
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Extract title
        try:
            title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
        except:
            title = "N/A"
        
        # Extract role
        try:
            role = driver.find_element(By.CSS_SELECTOR, "span.round-badge").text
        except:
            role = "N/A"

        # Extract description
        try:
            description = driver.find_element(By.CSS_SELECTOR, 'div[class*="experience-details"]').text
        except:
            # Try alternative selectors
            try:
                description = driver.find_element(By.CSS_SELECTOR, 'div[class*="content"]').text
            except:
                description = "N/A"

        return {
            "url": url,
            "title": title.strip(),
            "role": role.strip(),
            "description": description.strip()
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None
    finally:
        driver.quit()

# ✅ Threaded scraping of all links
def fetch_all_interviews(company, role, pages=1, max_threads=3):
    """
    Reduced max_threads to 3 to avoid overwhelming the server
    """
    print(f"Starting scraping for company: {company}, role: {role}")
    
    # Test driver first
    if not test_driver():
        print("Driver test failed. Please check your Chrome installation.")
        return pd.DataFrame()
    
    links = fetch_interview_links(company, role, pages)
    print(f"Found {len(links)} links")
    
    if not links:
        print("No links found. Check your search parameters.")
        return pd.DataFrame()

    data = []
    with ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {executor.submit(parse_interview_page, url): url for url in links}
        
        for i, future in enumerate(as_completed(future_to_url)):
            result = future.result()
            if result:
                data.append(result)
                print(f"Scraped {i+1}/{len(links)}: {result['title']}")
            else:
                print(f"Failed to scrape {i+1}/{len(links)}")

    return pd.DataFrame(data)

# Example usage
if __name__ == "__main__":
    # Test the setup
    print("Testing Chrome driver setup...")
    if test_driver():
        print("✅ Setup successful!")
        
        # Example scraping
        df = fetch_all_interviews("Google", "Software Engineer", pages=1, max_threads=2)
        print(f"Scraped {len(df)} interviews")
        print(df.head())
    else:
        print("❌ Setup failed. Please check Chrome installation.")
