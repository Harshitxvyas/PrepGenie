import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed


# Step 1: Fetch all interview links after applying filters
def fetch_interview_links(company_to_filter, role_to_filter, pages_to_scrape):
    print("--- Step 1: Fetching interview links ---")
    target_url = "https://www.naukri.com/code360/interview-experiences"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument('user-agent=Mozilla/5.0')

    driver = get_driver()
    wait = WebDriverWait(driver, 15)
    all_results = []

    try:
        driver.get(target_url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "codingninjas-interview-experience-card-v2")))

        # Filter Company
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-company-dropdown-widget > div"))).click()
        comp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search']")))
        comp_input.send_keys(company_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-radio-button.mat-radio-button"))).click()
        time.sleep(1)

        # Filter Role
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#right-section-container codingninjas-ie-roles-dropdown-widget:nth-child(2) > div"))).click()
        role_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget input[placeholder='Search']")))
        role_input.send_keys(role_to_filter)
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "codingninjas-ie-roles-dropdown-widget mat-checkbox"))).click()
        time.sleep(1)

        # Collect links
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

            # Go to next page
            if page < pages_to_scrape:
                try:
                    next_page_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//codingninjas-page-nav-v2//a[normalize-space(text())='{page + 1}']")))
                    driver.execute_script("arguments[0].click();", next_page_link)
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


# Step 2: Scrape content from individual interview URLs
def scrape_interview_details(url):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--log-level=3')
        options.add_argument('user-agent=Mozilla/5.0')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        driver.get(url)
        time.sleep(5)

        parts = []
        try:
            # Expand journey section
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

        # Extract rounds
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

                # Extract problem links by clicking
                links = []
                try:
                    problems = round_container.find_elements(By.CSS_SELECTOR, "codingninjas-interview-round-problem")
                    for prob in problems:
                        try:
                            link_btn = prob.find_element(By.CSS_SELECTOR, ".try-now-solve-later-container a")
                            original_window = driver.current_window_handle
                            driver.execute_script("arguments[0].click();", link_btn)
                            time.sleep(2)

                            WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(2))
                            new_window = [w for w in driver.window_handles if w != original_window][0]
                            driver.switch_to.window(new_window)
                            time.sleep(2)

                            current_url = driver.current_url
                            links.append(current_url)

                            driver.close()
                            driver.switch_to.window(original_window)

                        except Exception as e:
                            links.append("null")
                except:
                    links.append("null")

                safe_links_string = ", ".join(link for link in links if link and link != "null")
                round_text += f"\n\n🔗 Problem Links: {safe_links_string if safe_links_string else 'null'}"

                parts.append(f"\n\n### Round {round_index}\n{round_text}")
                round_index += 1

            except NoSuchElementException:
                break

        # Fallback
        if not parts:
            try:
                content = driver.find_element(By.CSS_SELECTOR, "div.blog-body-content").text.strip()
                if content:
                    parts.append(content)
            except:
                return None

        return "\n".join(parts)

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


# Step 3: Wrap scraper for threading
def scrape_link_wrapper(item, company_to_filter, role_to_filter_input):
    url = item.get('url') or item.get('URL')
    title = item.get('title') or item.get('Title')
    description = scrape_interview_details(url)

    if description:
        try:
            company, role = [part.strip() for part in title.split('|')]
        except:
            company = company_to_filter
            role = role_to_filter_input
        return {"company": company, "role": role, "description": description}
    return None


# Step 4: Main function
def main(company_to_filter, role_to_filter_input, pages_to_scrape):
    role_to_filter = re.sub(r'\s*-\s*', ' - ', role_to_filter_input).upper()
    pages_to_scrape = max(1, int(pages_to_scrape))

    # Step 1: Get links
    links_to_process = fetch_interview_links(company_to_filter, role_to_filter, pages_to_scrape)
    if not links_to_process:
        print("❌ No links found.")
        return None

    # Step 2: Parallel scrape
    print("\n--- Step 2: Scraping interview details in parallel ---")
    scraped_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(scrape_link_wrapper, item, company_to_filter, role_to_filter_input): item
            for item in links_to_process
        }
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"Scraped {i}/{len(links_to_process)}")
            if result:
                scraped_data.append(result)

    # Step 3: Return DataFrame
    if scraped_data:
        print(f"\n✅ Scraped {len(scraped_data)} interviews successfully.")
        return pd.DataFrame(scraped_data)
    else:
        print("\n❌ Failed to scrape any data.")
        return None
