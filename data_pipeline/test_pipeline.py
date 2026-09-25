import sqlite3

import pandas as pd
import pytest

from data_pipeline.pipeline import clean, load_database


def test_messy_rows_types_conversion_and_foreign_keys(tmp_path):
    base = {'title':'Book', 'price':'£20.00', 'star_rating':'Three', 'availability':'In stock', 'category':'Travel'}
    rows = [base, dict(base, title='Broken', price='N/A'),
            dict(base, title='Unknown', availability='maybe'),
            dict(base, title='Rating', star_rating='Six'),
            dict(base, title='Sold', availability='Out of stock')]
    result = clean(pd.DataFrame(rows))
    assert result.title.tolist() == ['Book','Sold']
    assert result.price_inr.tolist() == [2110.0,2110.0]
    assert result.rating.dtype.kind == 'i'
    assert result.in_stock.dtype.kind == 'b'
    assert result.in_stock.tolist() == [True, False]
    database = tmp_path / 'books.sqlite'
    load_database(result, database)
    load_database(result, database)  # Rerun from scratch does not accumulate duplicates.
    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        assert connection.execute('SELECT COUNT(*) FROM books').fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO books VALUES (3,'bad',1,105.5,3,1,999)")
