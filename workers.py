# import os
# import time
# import csv
# import requests

# from pdfminer.high_level import extract_text

# from urllib.parse import urljoin, urlparse, urlunparse
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

# from driver_utils import get_driver

# NON_HTML_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.7z')

# output_file = 'finfinfin.csv'
# already_saved_links = set()

# if os.path.exists(output_file):
#     with open(output_file, 'r', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             already_saved_links.add(row['url'])
#     print(f"[Init] Loaded {len(already_saved_links)} links from existing CSV.")


# def clean_url(url):
#     return url.rstrip('/')


# def get_domain_path(url):
#     parsed = urlparse(url)
#     return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


# def is_subpath(parent, child):
#     return get_domain_path(child).startswith(get_domain_path(parent))


# def normalize_url(url):
#     parsed = urlparse(url)
#     normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
#     return normalized


# def get_internal_links(driver, base_url):
#     soup = BeautifulSoup(driver.page_source, 'html.parser')
#     links = []
#     for a in soup.find_all('a', href=True):
#         href = urljoin(base_url, a['href'])
#         href_lower = href.lower()

#         if any(href_lower.endswith(ext) for ext in NON_HTML_EXTENSIONS):
#             continue

#         if 'print=y' in href_lower:
#             continue

#         if is_subpath(base_url, href):
#             normalized_href = normalize_url(href)
#             text = a.get_text(strip=True)
#             links.append((normalized_href, text))
#     print(f"[get_internal_links] Found {len(links)} internal links on {base_url}")
#     return links


# def contains_keyword(url, a_text, page_title, keywords):
#     url_lower = url.lower()
#     a_text_lower = (a_text or '').lower()
#     title_lower = (page_title or '').lower()

#     for kw in keywords:
#         kw_lower = kw.lower()
#         if kw_lower in url_lower:
#             return kw, 'url'
#         if kw_lower in a_text_lower:
#             return kw, 'a_text'
#         if kw_lower in title_lower:
#             return kw, 'title'
#     return None, None


# def scrape_company_task(args):
#     # company, root_url, inn, output_dir, lock, keywords_eng, keywords_ru = args
#     company, root_url, inn, output_dir, lock, keywords_eng, keywords_ru, pdf_mode = args
#     all_keywords = keywords_eng.union(keywords_ru)

#     print(f"[{company}] Starting scraping: {root_url}")

#     driver = get_driver()
#     visited_links = set()
#     results = []
#     link_count = 0

#     company_dir = os.path.join(output_dir, f"{company}_{inn}")
#     os.makedirs(company_dir, exist_ok=True)

#     def crawl_branch(link, a_text=None, depth=0, max_depth=5):
#         nonlocal link_count

#         normalized_link = normalize_url(link)
#         if depth > max_depth:
#             print(f"[{company}] Max depth reached at {normalized_link}")
#             return

#         if normalized_link in visited_links:
#             print(f"[{company}] Already visited: {normalized_link}")
#             return

#         if normalized_link in already_saved_links:
#             print(f"[{company}] Already saved (from file): {normalized_link}")
#             return

#         visited_links.add(normalized_link)

#         lower_link = normalized_link.lower()
#         if any(lower_link.endswith(ext) for ext in NON_HTML_EXTENSIONS) or 'print=y' in lower_link:
#             print(f"[{company}] Skipping non-HTML or print link: {normalized_link}")
#             return

#         try:
#             print(f"[{company}] Visiting {normalized_link} at depth {depth}")
#             driver.get(normalized_link)
#             time.sleep(1)
#             page_title = driver.title or ""

#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             page_text = soup.get_text(separator=' ', strip=True) or ""

#             matched_keyword, matched_tag = contains_keyword(normalized_link, a_text or "", page_title, all_keywords)

#             if matched_keyword:
#                 link_count += 1
#                 print(f"[{company}] Matched keyword '{matched_keyword}' in {matched_tag} at {normalized_link}")
#                 results.append([company, normalized_link, inn, page_text, matched_keyword, matched_tag])
#                 already_saved_links.add(normalized_link)

#             new_links = get_internal_links(driver, normalized_link)
#             print(f"[{company}] Found {len(new_links)} links to crawl from {normalized_link}")
#             for sub_link, sub_text in new_links:
#                 crawl_branch(sub_link, a_text=sub_text, depth=depth + 1, max_depth=max_depth)

#         except Exception as e:
#             print(f"[{company}] [Error crawling {normalized_link}] {e}")

#     try:
#         root_url_clean = normalize_url(clean_url(root_url))
#         print(f"[{company}] Starting from root URL: {root_url_clean}")
#         driver.get(root_url_clean)
#         time.sleep(1)
#         root_title = driver.title or ""

#         soup = BeautifulSoup(driver.page_source, 'html.parser')
#         root_page_text = soup.get_text(separator=' ', strip=True) or ""

#         matched_keyword, matched_tag = contains_keyword(root_url_clean, company, root_title, all_keywords)
#         if matched_keyword:
#             print(f"[{company}] Root page matched keyword '{matched_keyword}' in {matched_tag}")
#             results.append([company, root_url_clean, inn, root_page_text, matched_keyword, matched_tag])
#             already_saved_links.add(root_url_clean)
#         else:
#             print(f"[{company}] Root page has no keyword match")

#         initial_links = get_internal_links(driver, root_url_clean)
#         print(f"[{company}] Starting to crawl {len(initial_links)} initial links from root")
#         for link, a_text in initial_links:
#             crawl_branch(link, a_text=a_text, depth=1)

#         print(f"[{company}] ✅ Done. Total matched pages saved: {len(results)}")

#         with lock:
#             file_exists = os.path.exists(output_file)
#             with open(output_file, 'a', encoding='utf-8', newline='') as f:
#                 writer = csv.writer(f)
#                 if not file_exists:
#                     writer.writerow(['company', 'url', 'INN', 'web_page_text', 'matched_keyword', 'matched_tag_content'])
#                 writer.writerows(results)

#     except Exception as e:
#         print(f"[{company}] ❌ General error: {e}")

#     finally:
#         driver.quit()

import os
import time
import csv
import requests

from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from driver_utils import get_driver

NON_HTML_EXTENSIONS = ('.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.7z')  # .pdf excluded here

output_file = 'pdf-parsing-test.csv'
already_saved_links = set()

if os.path.exists(output_file):
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            already_saved_links.add(row['url'])
    print(f"[Init] Loaded {len(already_saved_links)} links from existing CSV.")


def clean_url(url):
    return url.rstrip('/')


def get_domain_path(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def is_subpath(parent, child):
    return get_domain_path(child).startswith(get_domain_path(parent))


def normalize_url(url):
    parsed = urlparse(url)
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
    return normalized


def get_internal_links(driver, base_url):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        href_lower = href.lower()

        if any(href_lower.endswith(ext) for ext in NON_HTML_EXTENSIONS):
            continue

        if 'print=y' in href_lower:
            continue

        if is_subpath(base_url, href):
            normalized_href = normalize_url(href)
            text = a.get_text(strip=True)
            links.append((normalized_href, text))
    print(f"[get_internal_links] Found {len(links)} internal links on {base_url}")
    return links


def contains_keyword(url, a_text, page_title, keywords):
    url_lower = url.lower()
    a_text_lower = (a_text or '').lower()
    title_lower = (page_title or '').lower()

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in url_lower:
            return kw, 'url'
        if kw_lower in a_text_lower:
            return kw, 'a_text'
        if kw_lower in title_lower:
            return kw, 'title'
    return None, None


def scrape_company_task(args):
    company, root_url, inn, output_dir, lock, keywords_eng, keywords_ru, pdf_mode = args
    all_keywords = keywords_eng.union(keywords_ru)

    print(f"[{company}] Starting scraping: {root_url}")

    driver = get_driver()
    visited_links = set()
    results = []
    link_count = 0

    company_dir = os.path.join(output_dir, f"{company}_{inn}")
    os.makedirs(company_dir, exist_ok=True)


    def handle_pdf(link):
        try:
            filename = os.path.basename(urlparse(link).path)
            filename_lower = filename.lower()

            # Check if any keyword is in the filename
            matched_kw = next((kw for kw in all_keywords if kw in filename_lower), None)
            if not matched_kw:
                print(f"[{company}] Skipping PDF '{filename}' (no keyword match)")
                return
            print(f"[{company}] Matched keyword '{matched_kw}' in PDF filename: {filename}")

            print(f"[{company}] Downloading PDF: {link}")
            response = requests.get(link, timeout=10)
            response.raise_for_status()

            if not filename_lower.endswith(".pdf"):
                filename = f"document_{hash(link)}.pdf"

            local_pdf_path = os.path.join(company_dir, filename)

            if os.path.exists(local_pdf_path):
                print(f"[{company}] PDF already exists: {local_pdf_path}")
                return

            with open(local_pdf_path, 'wb') as f:
                f.write(response.content)

            print(f"[{company}] PDF saved to: {local_pdf_path}")

        except Exception as e:
            print(f"[{company}] Error downloading PDF from {link}: {e}")


    def crawl_branch(link, a_text=None, depth=0, max_depth=5):
        nonlocal link_count

        normalized_link = normalize_url(link)
        if depth > max_depth:
            print(f"[{company}] Max depth reached at {normalized_link}")
            return

        if normalized_link in visited_links:
            print(f"[{company}] Already visited: {normalized_link}")
            return

        if normalized_link in already_saved_links:
            print(f"[{company}] Already saved (from file): {normalized_link}")
            return

        visited_links.add(normalized_link)

        lower_link = normalized_link.lower()

        if pdf_mode and lower_link.endswith('.pdf'):
            handle_pdf(normalized_link)
            return

        if any(lower_link.endswith(ext) for ext in NON_HTML_EXTENSIONS) or 'print=y' in lower_link:
            print(f"[{company}] Skipping non-HTML or print link: {normalized_link}")
            return

        try:
            print(f"[{company}] Visiting {normalized_link} at depth {depth}")
            driver.get(normalized_link)
            time.sleep(1)
            page_title = driver.title or ""

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True) or ""

            matched_keyword, matched_tag = contains_keyword(normalized_link, a_text or "", page_title, all_keywords)

            if matched_keyword:
                link_count += 1
                print(f"[{company}] Matched keyword '{matched_keyword}' in {matched_tag} at {normalized_link}")
                results.append([company, normalized_link, inn, page_text, matched_keyword, matched_tag])
                already_saved_links.add(normalized_link)

            new_links = get_internal_links(driver, normalized_link)
            print(f"[{company}] Found {len(new_links)} links to crawl from {normalized_link}")
            for sub_link, sub_text in new_links:
                crawl_branch(sub_link, a_text=sub_text, depth=depth + 1, max_depth=max_depth)

        except Exception as e:
            print(f"[{company}] [Error crawling {normalized_link}] {e}")

    try:
        root_url_clean = normalize_url(clean_url(root_url))
        print(f"[{company}] Starting from root URL: {root_url_clean}")
        driver.get(root_url_clean)
        time.sleep(1)
        root_title = driver.title or ""

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        root_page_text = soup.get_text(separator=' ', strip=True) or ""

        matched_keyword, matched_tag = contains_keyword(root_url_clean, company, root_title, all_keywords)
        if matched_keyword:
            print(f"[{company}] Root page matched keyword '{matched_keyword}' in {matched_tag}")
            results.append([company, root_url_clean, inn, root_page_text, matched_keyword, matched_tag])
            already_saved_links.add(root_url_clean)
        else:
            print(f"[{company}] Root page has no keyword match")

        initial_links = get_internal_links(driver, root_url_clean)
        print(f"[{company}] Starting to crawl {len(initial_links)} initial links from root")
        for link, a_text in initial_links:
            crawl_branch(link, a_text=a_text, depth=1)

        print(f"[{company}] ✅ Done. Total matched pages saved: {len(results)}")

        with lock:
            file_exists = os.path.exists(output_file)
            with open(output_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['company', 'url', 'INN', 'web_page_text', 'matched_keyword', 'matched_tag_content'])
                writer.writerows(results)

    except Exception as e:
        print(f"[{company}] ❌ General error: {e}")

    finally:
        driver.quit()
