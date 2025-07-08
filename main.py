import os
import pandas as pd
import multiprocessing

from tqdm import tqdm
from workers import scrape_company_task

PDF_DOWNLOAD_ENABLED = True
NEWS_ENABLED = True

def main():
    """
    Main function to initialize scraping pipeline for multiple companies.
    Loads input data and keyword sets, spawns multiprocessing tasks.
    """
    df = pd.read_excel('src/templates/sample.xlsx', sheet_name='Лист1')
    keywords_df = pd.read_excel('src/templates/keywords.xlsx', sheet_name='Лист2')
    news_keywords_df = pd.read_excel('src/templates/keywords.xlsx', sheet_name='news_keywords')

    # Convert keywords to lowercase sets for matching
    keywords_eng = set(keywords_df['keyword_eng'].dropna().str.lower())
    keywords_ru = set(keywords_df['keyword_ru'].dropna().str.lower())
    news_keywords = set(news_keywords_df['keyword'].dropna().str.lower())

    # Output directory for saving PDF-files
    output_dir = 'downloaded_data'

    os.makedirs(output_dir, exist_ok=True)

    manager = multiprocessing.Manager()
    lock = manager.Lock()

    company_args = [
        (
            row['company'],
            row['url'],
            row['INN'],
            output_dir,
            lock,
            keywords_eng,
            keywords_ru,
            PDF_DOWNLOAD_ENABLED,
            NEWS_ENABLED,
            news_keywords
        )
        for _, row in df.iterrows()
    ]   

    # Use multiprocessing pool for concurrent scraping
    with multiprocessing.Pool(processes=4) as pool:
        list(tqdm(pool.imap_unordered(scrape_company_task, company_args), total=len(company_args)))

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()