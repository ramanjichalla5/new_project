"""Scrape five catalogue pages, normalize SQLite, and execute auditable queries."""
from pathlib import Path
from urllib.parse import urljoin
import re
import sqlite3
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RATE = 105.50
RATINGS = dict(zip(['One', 'Two', 'Three', 'Four', 'Five'], range(1, 6)))
BASE = 'https://books.toscrape.com/'


def scrape():
    session = requests.Session()
    session.headers['User-Agent'] = 'ZeptoCapstone/1.0 (educational scraping)'
    session.mount('https://', HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])))

    def page(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return BeautifulSoup(response.text, 'html.parser')

    rows = []
    for number in range(1, 6):
        listing_url = urljoin(BASE, f'catalogue/page-{number}.html')
        listing = page(listing_url)
        cards = listing.select('article.product_pod')
        if not cards:
            raise RuntimeError(f'No catalogue cards at {listing_url}')
        for card in cards:
            link = card.select_one('h3 a')
            detail_url = urljoin(listing_url, link['href'])
            detail = page(detail_url)
            category = detail.select('ul.breadcrumb li')[-2].get_text(strip=True)
            rating = card.select_one('.star-rating')
            rows.append({'title': link['title'],
                         'price': card.select_one('.price_color').get_text(strip=True),
                         'star_rating': next((x for x in rating['class'] if x != 'star-rating'), ''),
                         'availability': card.select_one('.availability').get_text(' ', strip=True),
                         'category': category})
            time.sleep(0.05)
        print(f'Scraped page {number}: {len(rows)} books', flush=True)
    session.close()
    return pd.DataFrame(rows)


def clean(raw):
    """Drop malformed rows: inventing product facts would distort comparisons."""
    rows = []
    for row in raw.to_dict('records'):
        try:
            match = re.fullmatch(r'\s*£?(\d+(?:\.\d{1,2})?)\s*', str(row['price']))
            if not match:
                continue
            availability = re.sub(r'\s+', ' ', str(row['availability'])).strip().lower()
            if re.fullmatch(r'in stock(?: \(\d+ available\))?', availability):
                stock = True
            elif availability in ('out of stock', 'unavailable'):
                stock = False
            else:
                continue
            title, category = str(row['title']).strip(), str(row['category']).strip()
            if not title or not category or title == 'nan' or category == 'nan':
                continue
            price = float(match.group(1))
            rows.append(dict(title=title, price_gbp=price, price_inr=round(price * RATE, 2),
                             rating=RATINGS[row['star_rating']], in_stock=stock, category=category))
        except (KeyError, TypeError, ValueError):
            continue
    if not rows:
        raise ValueError('No valid book rows remain after cleaning')
    result = pd.DataFrame(rows).drop_duplicates(['title', 'category']).reset_index(drop=True)
    return result.astype({'price_gbp': float, 'price_inr': float, 'rating': int, 'in_stock': bool})


def load_database(frame, path):
    categories = pd.DataFrame({'category': sorted(frame.category.unique())})
    categories.insert(0, 'category_id', range(1, len(categories) + 1))
    books = frame.merge(categories, on='category').drop(columns='category')
    books.insert(0, 'book_id', range(1, len(books) + 1))
    with sqlite3.connect(path) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript('''
            DROP TABLE IF EXISTS books;
            DROP TABLE IF EXISTS categories;
            CREATE TABLE categories (
                category_id INTEGER PRIMARY KEY, category TEXT NOT NULL UNIQUE);
            CREATE TABLE books (
                book_id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                price_gbp REAL NOT NULL CHECK(price_gbp >= 0),
                price_inr REAL NOT NULL CHECK(price_inr >= 0),
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                in_stock INTEGER NOT NULL CHECK(in_stock IN (0, 1)),
                category_id INTEGER NOT NULL REFERENCES categories(category_id));
        ''')
        connection.executemany('INSERT INTO categories VALUES (?, ?)', categories.itertuples(index=False, name=None))
        connection.executemany('INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?)', books.itertuples(index=False, name=None))
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    return books, categories


def run():
    runtime = ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    raw = scrape()
    frame = clean(raw)
    if len(frame) < 60 or frame.category.nunique() < 3:
        raise RuntimeError('Acceptance requires at least 60 books and 3 categories')
    frame.to_csv(HERE / 'books.csv', index=False)
    books, categories = load_database(frame, runtime / 'catalogue.sqlite')
    queries = [q.strip() for q in (HERE / 'queries.sql').read_text().split(';') if q.strip()]
    sections = ['# Executed catalogue results',
                f'{len(raw)} scraped rows → {len(frame)} clean rows; {frame.category.nunique()} categories. '
                f'Dropped {len(raw) - len(frame)} malformed/duplicate rows. Fixed project rate: 1 GBP = 105.50 INR.',
                'Malformed prices, unknown ratings, unrecognized availability, or empty title/category are dropped. '
                'This avoids inventing catalogue facts; conversion rounds to two decimal places.',
                '## Cleaned dtypes', '```text\n' + str(frame.dtypes) + '\n```']
    with sqlite3.connect(runtime / 'catalogue.sqlite') as connection:
        for index, query in enumerate(queries, 1):
            # Every query (not just two) is read with pandas.read_sql.
            output = pd.read_sql(query, connection)
            sections.extend([f'## Query {index}', f'```sql\n{query};\n```', output.to_markdown(index=False)])
        sql_join = pd.read_sql(queries[-1], connection)
    pandas_join = pd.merge(books, categories, on='category_id')
    pandas_join = pandas_join.loc[pandas_join.rating >= 4, ['title', 'category', 'rating', 'price_inr']]
    pandas_join = pandas_join.sort_values(['rating', 'title'], ascending=[False, True]).head(10).reset_index(drop=True)
    pd.testing.assert_frame_equal(sql_join, pandas_join, check_dtype=False)
    side_by_side = pd.concat([sql_join.add_prefix('SQL: '), pandas_join.add_prefix('pandas: ')], axis=1)
    sections.extend(['## SQL JOIN versus in-memory pd.merge', side_by_side.to_markdown(index=False),
                     'PASS: pandas.testing.assert_frame_equal confirms identical values and row order.'])
    (HERE / 'RESULTS.md').write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    print('\n\n'.join(sections))


if __name__ == '__main__':
    run()
