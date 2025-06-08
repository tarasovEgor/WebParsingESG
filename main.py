import pandas as pd
import os
import multiprocessing

from tqdm import tqdm
from workers import scrape_company_task

def main():
    df = pd.read_excel('src/templates/sample.xlsx', sheet_name='Лист1')
    keywords_df = pd.read_excel('src/templates/keywords.xlsx', sheet_name='Лист2')

    keywords_eng = set(keywords_df['keyword_eng'].dropna().str.lower())
    keywords_ru = set(keywords_df['keyword_ru'].dropna().str.lower())

    output_dir = 'downloaded_data'
    os.makedirs(output_dir, exist_ok=True)

    manager = multiprocessing.Manager()
    lock = manager.Lock()

    company_args = [
        (row['company'], row['url'], row['INN'], output_dir, lock, keywords_eng, keywords_ru)
        for _, row in df.iterrows()
    ]

    with multiprocessing.Pool(processes=4) as pool:
        list(tqdm(pool.imap_unordered(scrape_company_task, company_args), total=len(company_args)))

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()