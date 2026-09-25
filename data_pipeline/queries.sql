SELECT title, price_gbp FROM books WHERE in_stock = 1 ORDER BY price_gbp LIMIT 10;
SELECT title, rating FROM books WHERE rating IN (4, 5) ORDER BY rating DESC, title LIMIT 10;
SELECT title, price_inr FROM books WHERE price_gbp BETWEEN 20 AND 30 ORDER BY price_gbp LIMIT 10;
SELECT DISTINCT rating FROM books ORDER BY rating;
SELECT c.category, COUNT(*) AS book_count, ROUND(AVG(b.price_inr), 2) AS mean_price_inr FROM books b JOIN categories c ON b.category_id = c.category_id GROUP BY c.category ORDER BY book_count DESC, c.category;
SELECT b.title, c.category, b.rating, b.price_inr FROM books b JOIN categories c ON b.category_id = c.category_id WHERE b.rating >= 4 ORDER BY b.rating DESC, b.title LIMIT 10;
