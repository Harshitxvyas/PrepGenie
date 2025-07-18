import pandas as pd
import time
import os
import subprocess
import shutil
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st

# Streamlit Cloud environment setup
os.environ["STREAMLIT_DISABLE_WATCHDOG_WARNINGS"] = "true"
os.environ["STREAMLIT_WATCH_MODE"] = "poll"

# Streamlit Cloud paths
CHROMEDRIVER_PATH = "/tmp/chromedriver"
CHROME_BINARY_PATH = "/usr/bin/google-chrome"

@st.cache_resource
def setup_chrome_for_streamlit():
    """
    Setup Chrome and ChromeDriver for Streamlit Cloud
    This function is cached to avoid repeated setup
    """
    try:
        # Check if Chrome is already installed
        if os.path.exists(CHROME_BINARY_PATH):
            st.success("✅ Chrome found at system location")
            return True
            
        # Install Chrome if not found
        st.info("📥 Installing Chrome for Streamlit Cloud...")
        
        # Update package list
        subprocess.run(["apt-get", "update"], check=True, capture_output=True)
        
        # Install dependencies
        subprocess.run([
            "apt-get", "install", "-y", 
            "wget", "gnupg", "software-properties-common", "apt-transport-https", "ca-certificates"
        ], check=True, capture_output=True)
        
        # Add Google Chrome repository
        subprocess.run([
            "wget", "-q", "-O", "-", 
            "https://dl.google.com/linux/linux_signing_key.pub"
        ], stdout=subprocess.PIPE, check=True)
        
        subprocess.run([
            "apt-key", "add", "-"
        ], input=subprocess.run([
            "wget", "-q", "-O", "-", 
            "https://dl.google.com/linux/linux_signing_key.pub"
        ], capture_output=True).stdout, check=True)
        
        # Add Chrome repository
        with open("/etc/apt/sources.list.d/google-chrome.list", "w") as f:
            f.write("deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\n")
        
        # Update and install Chrome
        subprocess.run(["apt-get", "update"], check=True, capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "google-chrome-stable"], check=True, capture_output=True)
        
        st.success("✅ Chrome installed successfully")
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to install Chrome: {e}")
        return False

def download_chromedriver():
    """Download and setup ChromeDriver for Streamlit Cloud"""
    try:
        if os.path.exists(CHROMEDRIVER_PATH):
            st.info("✅ ChromeDriver already exists")
            return True
            
        st.info("📥 Downloading ChromeDriver...")
        
        # Use a more recent and stable version
        url = "https://storage.googleapis.com/chrome-for-testing-public/119.0.6045.105/linux64/chromedriver-linux64.zip"
        zip_path = "/tmp/chromedriver.zip"
        
        # Download ChromeDriver
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract ChromeDriver
        subprocess.run(["unzip", "-o", zip_path, "-d", "/tmp/"], check=True)
        
        # Find the chromedriver executable
        extracted_path = "/tmp/chromedriver-linux64/chromedriver"
        if not os.path.exists(extracted_path):
            # Try alternative extraction paths
            for root, dirs, files in os.walk("/tmp/"):
                for file in files:
                    if file == "chromedriver":
                        extracted_path = os.path.join(root, file)
                        break
        
        if not os.path.exists(extracted_path):
            raise Exception("ChromeDriver not found after extraction")
        
        # Make executable and copy to final location
        subprocess.run(["chmod", "+x", extracted_path], check=True)
        shutil.copy(extracted_path, CHROMEDRIVER_PATH)
        
        st.success("✅ ChromeDriver downloaded and setup successfully")
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to download ChromeDriver: {e}")
        return False

def get_chrome_driver():
    """Get Chrome driver optimized for Streamlit Cloud"""
    chrome_options = Options()
    
    # Essential options for Streamlit Cloud
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # For faster loading
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    # Memory optimization
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    
    # Set binary location
    chrome_options.binary_location = CHROME_BINARY_PATH
    
    try:
        # Use the manually downloaded ChromeDriver
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"❌ Failed to create Chrome driver: {e}")
        raise e

def test_driver():
    """Test if the driver works correctly"""
    try:
        with st.spinner("🧪 Testing Chrome driver..."):
            driver = get_chrome_driver()
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()
            if "Google" in title:
                st.success("✅ Driver test successful!")
                return True
            else:
                st.error("❌ Driver test failed: unexpected page title")
                return False
    except Exception as e:
        st.error(f"❌ Driver test failed: {e}")
        return False

def fetch_interview_links(company: str, role: str, pages: int = 1):
    """Scrape interview links with progress tracking"""
    base_url = "https://www.codingninjas.com/studio/experiences"
    search_url = f"{base_url}?company={company}&title={role}"
    
    driver = get_chrome_driver()
    links = set()
    
    try:
        with st.spinner(f"🔍 Fetching interview links for {company} - {role}..."):
            driver.get(search_url)
            time.sleep(3)
            
            progress_bar = st.progress(0)
            
            for page in range(pages):
                progress_bar.progress((page + 1) / pages)
                st.write(f"📄 Scraping page {page + 1}/{pages}")
                
                try:
                    # Wait for page to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Find interview links
                    elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/experiences/")]')
                    page_links = 0
                    
                    for el in elements:
                        href = el.get_attribute("href")
                        if href and "/experiences/" in href:
                            links.add(href)
                            page_links += 1
                    
                    st.write(f"   ✅ Found {page_links} links on page {page + 1}")
                    
                    # Try to go to next page
                    if page < pages - 1:
                        try:
                            next_button = driver.find_element(By.XPATH, '//button[contains(text(), "Next")]')
                            if next_button.is_enabled():
                                next_button.click()
                                time.sleep(3)
                            else:
                                st.write("   ⏭️ No more pages available")
                                break
                        except NoSuchElementException:
                            st.write("   ⏭️ Next button not found, stopping pagination")
                            break
                            
                except Exception as e:
                    st.error(f"❌ Error on page {page + 1}: {e}")
                    break
            
            progress_bar.progress(1.0)
            
    finally:
        driver.quit()
    
    return list(links)

def parse_interview_page(url):
    """Extract data from one interview URL"""
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
        st.error(f"❌ Error scraping {url}: {e}")
        return None
    finally:
        driver.quit()

def fetch_all_interviews(company, role, pages=1, max_threads=2):
    """
    Main function to fetch all interviews with Streamlit integration
    Reduced max_threads to 2 for Streamlit Cloud stability
    """
    st.header(f"🎯 Scraping Interviews: {company} - {role}")
    
    # Setup Chrome
    if not setup_chrome_for_streamlit():
        st.error("❌ Failed to setup Chrome")
        return pd.DataFrame()
    
    # Download ChromeDriver
    if not download_chromedriver():
        st.error("❌ Failed to setup ChromeDriver")
        return pd.DataFrame()
    
    # Test driver
    if not test_driver():
        st.error("❌ Driver test failed")
        return pd.DataFrame()
    
    # Fetch links
    links = fetch_interview_links(company, role, pages)
    
    if not links:
        st.warning("⚠️ No interview links found")
        return pd.DataFrame()
    
    st.success(f"✅ Found {len(links)} interview links")
    
    # Parse interviews
    data = []
    with st.spinner("🔍 Extracting interview data..."):
        progress_bar = st.progress(0)
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_url = {executor.submit(parse_interview_page, url): url for url in links}
            
            for i, future in enumerate(as_completed(future_to_url)):
                result = future.result()
                if result:
                    data.append(result)
                    st.write(f"✅ Scraped {i+1}/{len(links)}: {result['title']}")
                else:
                    st.write(f"❌ Failed to scrape {i+1}/{len(links)}")
                
                progress_bar.progress((i + 1) / len(links))
    
    df = pd.DataFrame(data)
    st.success(f"🎉 Successfully scraped {len(df)} interviews!")
    
    return df

# Streamlit UI
def main():
    st.title("🎯 Interview Experience Scraper")
    st.markdown("Scrape interview experiences from Coding Ninjas")
    
    # Input fields
    col1, col2, col3 = st.columns(3)
    
    with col1:
        company = st.text_input("Company Name", value="Google", help="Enter the company name")
    
    with col2:
        role = st.text_input("Role", value="Software Engineer", help="Enter the role/position")
    
    with col3:
        pages = st.number_input("Pages to Scrape", min_value=1, max_value=5, value=1, help="Number of pages to scrape (max 5)")
    
    if st.button("🚀 Start Scraping", type="primary"):
        if company and role:
            try:
                # Fetch interviews
                df = fetch_all_interviews(company, role, pages)
                
                if not df.empty:
                    # Display results
                    st.subheader("📊 Scraped Data")
                    st.dataframe(df)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"{company}_{role}_interviews.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ No data scraped")
                    
            except Exception as e:
                st.error(f"❌ Error during scraping: {e}")
        else:
            st.error("❌ Please enter both company name and role")

if __name__ == "__main__":
    main()
