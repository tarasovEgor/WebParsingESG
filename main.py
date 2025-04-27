import pandas as pd
import os
import csv
import multiprocessing
from workers import scrape_company_task


def main():
    df = pd.read_excel('src/templates/input_links_building.xlsx', sheet_name='Лист1')
    output_dir = 'downloaded_data'
    os.makedirs(output_dir, exist_ok=True)

    with open('scraped_output_building.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['company', 'url', 'INN', 'web_page_text'])

    lock = multiprocessing.Manager().Lock()

    company_args = [
        (row['company'], row['url'], row['INN'], output_dir, lock)
        for _, row in df.iterrows()
    ]

    with multiprocessing.Pool(processes=4) as pool:
        pool.map(scrape_company_task, company_args)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
