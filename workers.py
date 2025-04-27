import os
import time
import requests
import csv

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from multiprocessing import Lock


def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def get_internal_links(driver, base_url):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            href = urljoin(base_url, href)
        if base_url in href:
            links.add(href)
    return list(links)


def get_page_text(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text(separator=' ', strip=True)


def get_sitemap_links(base_url, filter_years=['2023', '2024', '2025']):
    sitemap_index_url = urljoin(base_url, '/sitemap.xml')
    filtered_links = set()
    all_links = set()

    def should_include(lastmod_text, loc_text):
        if not filter_years:
            return True
        return any(year in (lastmod_text or '') for year in filter_years) or \
               any(year in (loc_text or '') for year in filter_years)

    def is_sitemap_url(link):
        return link.endswith('.xml') or 'sitemap' in link.lower()

    try:
        res = requests.get(sitemap_index_url, timeout=10)
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.content, 'xml')

        if soup.find('sitemapindex'):
            for sitemap in soup.find_all('sitemap'):
                loc = sitemap.find('loc')
                if loc:
                    child_url = loc.text
                    try:
                        child_res = requests.get(child_url, timeout=10)
                        if child_res.status_code == 200:
                            child_soup = BeautifulSoup(child_res.content, 'xml')
                            for url_tag in child_soup.find_all('url'):
                                loc_tag = url_tag.find('loc')
                                lastmod_tag = url_tag.find('lastmod')
                                if loc_tag:
                                    url = loc_tag.text
                                    if not is_sitemap_url(url):
                                        all_links.add(url)
                                        if should_include(lastmod_tag.text if lastmod_tag else '', url):
                                            filtered_links.add(url)
                    except Exception as e:
                        print(f"[Child sitemap error] {child_url} – {e}")
        else:
            for url_tag in soup.find_all('url'):
                loc_tag = url_tag.find('loc')
                lastmod_tag = url_tag.find('lastmod')
                if loc_tag:
                    url = loc_tag.text
                    if not is_sitemap_url(url):
                        all_links.add(url)
                        if should_include(lastmod_tag.text if lastmod_tag else '', url):
                            filtered_links.add(url)

    except Exception as e:
        print(f"[Sitemap error] {sitemap_index_url} – {e}")

    final_links = filtered_links if len(filtered_links) > 3 else all_links
    final_links.add(base_url.rstrip('/'))

    return list(final_links)


def download_pdfs(driver, base_url, company_inn_folder):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    pdf_urls = set()

    required_keywords = ['отчет', 'доклад', 'устойчив', 'esg', 'отчёт', 'соц', 'эколог', 'ответствен']
    blacklist_keywords = ['белые ночи', 'д.2', 'корп.', 'изменения', 'заявление', 'разрешение']

    def is_relevant(pdf_url):
        filename = os.path.basename(urlparse(pdf_url).path).lower()
        if any(bad in filename for bad in blacklist_keywords):
            return False
        return any(good in filename for good in required_keywords)

    for tag in soup.find_all(['a', 'iframe', 'embed']):
        href = tag.get('href') or tag.get('src')
        if href and href.lower().endswith('.pdf'):
            full_url = href if href.startswith('http') else urljoin(base_url, href)
            if is_relevant(full_url):
                pdf_urls.add(full_url)

    os.makedirs(company_inn_folder, exist_ok=True)

    for pdf_url in pdf_urls:
        try:
            pdf_name = os.path.basename(urlparse(pdf_url).path)
            pdf_path = os.path.join(company_inn_folder, pdf_name)
            if os.path.exists(pdf_path):
                continue

            print(f"Downloading PDF: {pdf_url}")
            r = requests.get(pdf_url, timeout=10)
            r.raise_for_status()
            with open(pdf_path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"[PDF error] {pdf_url}: {e}")


def scrape_company_task(args):
    company, url, inn, output_dir, lock = args
    driver = init_driver()
    parsed_links = set()
    company_inn_folder = os.path.join(output_dir, f"{company}_{inn}")
    os.makedirs(company_inn_folder, exist_ok=True)

    def parse_link(link):
        if link in parsed_links or link.endswith('.xml'):
            return
        parsed_links.add(link)
        try:
            driver.get(link)
            time.sleep(2)
            text = get_page_text(driver)
            if "404" in text and ("not found" in text.lower() or "страница не найдена" in text.lower()):
                return

            download_pdfs(driver, link, company_inn_folder)

            with lock:
                with open('scraped_output_building.csv', 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([company, link, inn, text])
        except Exception as e:
            print(f"[Parse error] {link}: {e}")

    try:
        driver.get(url)
        time.sleep(2)
        links = get_internal_links(driver, url)
        links.insert(0, url)

        for link in links:
            parse_link(link)

        for sitemap_link in get_sitemap_links(url):
            parse_link(sitemap_link)

    except Exception as e:
        print(f"[{company}] Task error: {e}")
    finally:
        driver.quit()