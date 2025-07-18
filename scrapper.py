import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import pandas as pd
import requests
import time

BASE_URL = "https://www.geeksforgeeks.org/interview-experiences/experienced-interview-experiences-company-wise/"

def infer_role_and_years(title):
    m = re.search(r'(\d+(\.\d+)?)\s*(?:yr|year)', title, re.IGNORECASE)
    yrs = float(m.group(1)) if m else 0.0
    if yrs <= 2:
        role = "SDE-1"
    elif yrs <= 5:
        role = "SDE-2"
    else:
        role = "SDE-3"
    return yrs, role

def get_company_interview_df(company: str) -> pd.DataFrame:
    """
    Scrape GeeksforGeeks interview experiences for a specific company
    and return a pandas DataFrame with Title, Link, Years, and Role.
    """
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    company_label = company.strip().capitalize() + " :"
    company_node = soup.find(string=re.compile(f'^{re.escape(company_label)}$', re.IGNORECASE))

    if not company_node:
        print(f"❌ Company '{company}' not found.")
        return pd.DataFrame()

    entries = []
    for elem in company_node.next_elements:
        if isinstance(elem, NavigableString) and re.match(r'^\s*[A-Za-z0-9 &]+\s*:$', elem.strip()) \
           and elem.strip().lower() != company_label.lower():
            break

        if isinstance(elem, Tag) and elem.name == "a" and elem.get("href"):
            title = elem.get_text(strip=True)
            link = elem["href"]
            yrs, role = infer_role_and_years(title)
            entries.append({
                "Company": company.capitalize(),
                "Title": title,
                "Link": link,
                "Years": yrs,
                "Role": role
            })

    return pd.DataFrame(entries)


def fetch_full_text(link):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        resp = requests.get(link, headers=headers, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        text_div = soup.find("div", class_="text") or \
                   soup.find("div", class_="entry-content") or \
                   soup.find("article") or \
                   soup.find("div", class_="content") or \
                   soup.body

        if not text_div:
            return "Content div not found"

        full_experience = []
        strong_tags = text_div.find_all('strong')

        if not strong_tags:
            clean_text = text_div.get_text(separator=' ', strip=True)
            return re.sub(r'\s+', ' ', clean_text)

        for i, strong in enumerate(strong_tags):
            round_title = strong.get_text(strip=True)
            round_keywords = ['round', 'interview', 'telephonic', 'f2f', 'phone', 'onsite',
                              'technical', 'hr', 'managerial', 'written', 'coding', 'design',
                              'screening', 'assessment', 'test']

            if not any(keyword in round_title.lower() for keyword in round_keywords):
                if not re.match(r'.*round\s*\d+', round_title.lower()):
                    continue

            content_parts = []
            current = strong.next_sibling

            while current:
                if hasattr(current, 'name') and current.name == 'strong':
                    next_strong_text = current.get_text(strip=True)
                    if any(keyword in next_strong_text.lower() for keyword in round_keywords) or \
                       re.match(r'.*round\s*\d+', next_strong_text.lower()):
                        break

                if isinstance(current, str):
                    content_parts.append(current)
                else:
                    content_parts.append(str(current))

                current = current.next_sibling

            round_content = ''.join(content_parts).strip()
            round_content = re.sub(r'\s+', ' ', round_content)
            round_content = re.sub(r'<!--.*?-->', '', round_content, flags=re.DOTALL)
            round_content = re.sub(r'</?div[^>]*>', '', round_content)

            if round_content:
                full_experience.append(f"<h3>{round_title}</h3>\n{round_content}\n")

        result = '\n'.join(full_experience) if full_experience else text_div.get_text(separator=' ', strip=True)
        return re.sub(r'\n\s*\n\s*\n+', '\n\n', result.strip())

    except requests.RequestException as e:
        return f"Network error: {str(e)}"
    except Exception as e:
        return f"Parsing error: {str(e)}"


def add_interview_experiences(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame with a 'Link' column, scrape each URL
    and add an 'Interview_Experience' column.
    """
    experiences = []
    for idx, row in df.iterrows():
        link = row.get("Link", "")
        title = row.get("Title", "N/A")
        print(f"Fetching ({idx+1}/{len(df)}): {title[:50]}...")

        try:
            if idx > 0:
                time.sleep(2)  # Be polite to the server
            content = fetch_full_text(link)
        except Exception as e:
            content = f"Unexpected error: {str(e)}"

        experiences.append(content)

    df = df.copy()
    df["Interview_Experience"] = experiences
    df["Interview_Experience"] = df["Interview_Experience"].astype(str).apply(
    lambda x: BeautifulSoup(x, "html.parser").get_text(separator=' ', strip=True)
)
    return df
