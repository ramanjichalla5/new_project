# Executed catalogue results

100 scraped rows → 100 clean rows; 29 categories. Dropped 0 malformed/duplicate rows. Fixed project rate: 1 GBP = 105.50 INR.

Malformed prices, unknown ratings, unrecognized availability, or empty title/category are dropped. This avoids inventing catalogue facts; conversion rounds to two decimal places.

## Cleaned dtypes

```text
title         object
price_gbp    float64
price_inr    float64
rating         int64
in_stock        bool
category      object
dtype: object
```

## Query 1

```sql
SELECT title, price_gbp FROM books WHERE in_stock = 1 ORDER BY price_gbp LIMIT 10;
```

| title                                                                               |   price_gbp |
|:------------------------------------------------------------------------------------|------------:|
| Patience                                                                            |       10.16 |
| In Her Wake                                                                         |       12.84 |
| Princess Between Worlds (Wide-Awake Princess #5)                                    |       13.34 |
| Princess Jellyfish 2-in-1 Omnibus, Vol. 01 (Princess Jellyfish 2-in-1 Omnibus #1)   |       13.61 |
| Starving Hearts (Triangular Trade Trilogy, #1)                                      |       13.99 |
| Mama Tried: Traditional Italian Cooking for the Screwed, Crude, Vegan, and Tattooed |       14.02 |
| On a Midnight Clear                                                                 |       14.07 |
| Untitled Collection: Sabbath Poems 2014                                             |       14.27 |
| Obsidian (Lux #1)                                                                   |       14.86 |
| Outcast, Vol. 1: A Darkness Surrounds Him (Outcast #1)                              |       15.44 |

## Query 2

```sql
SELECT title, rating FROM books WHERE rating IN (4, 5) ORDER BY rating DESC, title LIMIT 10;
```

| title                                                                             |   rating |
|:----------------------------------------------------------------------------------|---------:|
| #HigherSelfie: Wake Up Your Life. Free Your Soul. Find Your Tribe.                |        5 |
| Black Dust                                                                        |        5 |
| Chase Me (Paris Nights #2)                                                        |        5 |
| Join                                                                              |        5 |
| Princess Between Worlds (Wide-Awake Princess #5)                                  |        5 |
| Princess Jellyfish 2-in-1 Omnibus, Vol. 01 (Princess Jellyfish 2-in-1 Omnibus #1) |        5 |
| Private Paris (Private #10)                                                       |        5 |
| Rip it Up and Start Again                                                         |        5 |
| Sapiens: A Brief History of Humankind                                             |        5 |
| Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)                           |        5 |

## Query 3

```sql
SELECT title, price_inr FROM books WHERE price_gbp BETWEEN 20 AND 30 ORDER BY price_gbp LIMIT 10;
```

| title                                                                                                                                                  |   price_inr |
|:-------------------------------------------------------------------------------------------------------------------------------------------------------|------------:|
| The Inefficiency Assassin: Time Management Tactics for Working Smarter, Not Longer                                                                     |     2172.24 |
| Shakespeare's Sonnets                                                                                                                                  |     2179.63 |
| In the Country We Love: My Family Divided                                                                                                              |     2321    |
| America's Cradle of Quarterbacks: Western Pennsylvania's Football Factory from Johnny Unitas to Joe Montana                                            |     2373.75 |
| The Boys in the Boat: Nine Americans and Their Epic Quest for Gold at the 1936 Berlin Olympics                                                         |     2384.3  |
| The Requiem Red                                                                                                                                        |     2389.57 |
| #HigherSelfie: Wake Up Your Life. Free Your Soul. Find Your Tribe.                                                                                     |     2438.11 |
| The Elephant Tree                                                                                                                                      |     2513.01 |
| Olio                                                                                                                                                   |     2519.34 |
| The Mindfulness and Acceptance Workbook for Anxiety: A Guide to Breaking Free from Anxiety, Phobias, and Worry Using Acceptance and Commitment Therapy |     2520.39 |

## Query 4

```sql
SELECT DISTINCT rating FROM books ORDER BY rating;
```

|   rating |
|---------:|
|        1 |
|        2 |
|        3 |
|        4 |
|        5 |

## Query 5

```sql
SELECT c.category, COUNT(*) AS book_count, ROUND(AVG(b.price_inr), 2) AS mean_price_inr FROM books b JOIN categories c ON b.category_id = c.category_id GROUP BY c.category ORDER BY book_count DESC, c.category;
```

| category           |   book_count |   mean_price_inr |
|:-------------------|-------------:|-----------------:|
| Sequential Art     |           14 |          3366.13 |
| Nonfiction         |           12 |          3426.9  |
| Default            |            9 |          2832.44 |
| Poetry             |            7 |          3823.17 |
| Add a comment      |            5 |          3201.08 |
| Fiction            |            5 |          4628.49 |
| Food and Drink     |            5 |          3680.47 |
| Fantasy            |            4 |          2994.62 |
| History            |            4 |          3580.67 |
| Young Adult        |            4 |          2642.51 |
| Childrens          |            3 |          5192.71 |
| Music              |            3 |          4557.25 |
| Mystery            |            3 |          4358.91 |
| Thriller           |            3 |          3125.61 |
| Philosophy         |            2 |          3906.14 |
| Romance            |            2 |          3154.45 |
| Science Fiction    |            2 |          3864.47 |
| Spirituality       |            2 |          2632.23 |
| Art                |            1 |          4660.99 |
| Business           |            1 |          3517.37 |
| Contemporary       |            1 |          3351.74 |
| Health             |            1 |          5174.77 |
| Historical Fiction |            1 |          5669.57 |
| Horror             |            1 |          4140.88 |
| New Adult          |            1 |          4754.89 |
| Politics           |            1 |          5415.31 |
| Science            |            1 |          4532.28 |
| Self Help          |            1 |          4889.93 |
| Travel             |            1 |          4765.44 |

## Query 6

```sql
SELECT b.title, c.category, b.rating, b.price_inr FROM books b JOIN categories c ON b.category_id = c.category_id WHERE b.rating >= 4 ORDER BY b.rating DESC, b.title LIMIT 10;
```

| title                                                                             | category        |   rating |   price_inr |
|:----------------------------------------------------------------------------------|:----------------|---------:|------------:|
| #HigherSelfie: Wake Up Your Life. Free Your Soul. Find Your Tribe.                | Nonfiction      |        5 |     2438.11 |
| Black Dust                                                                        | Romance         |        5 |     3642.91 |
| Chase Me (Paris Nights #2)                                                        | Romance         |        5 |     2665.99 |
| Join                                                                              | Science Fiction |        5 |     3763.19 |
| Princess Between Worlds (Wide-Awake Princess #5)                                  | Fantasy         |        5 |     1407.37 |
| Princess Jellyfish 2-in-1 Omnibus, Vol. 01 (Princess Jellyfish 2-in-1 Omnibus #1) | Sequential Art  |        5 |     1435.86 |
| Private Paris (Private #10)                                                       | Fiction         |        5 |     5022.85 |
| Rip it Up and Start Again                                                         | Music           |        5 |     3694.61 |
| Sapiens: A Brief History of Humankind                                             | History         |        5 |     5721.26 |
| Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)                           | Sequential Art  |        5 |     5516.6  |

## SQL JOIN versus in-memory pd.merge

| SQL: title                                                                        | SQL: category   |   SQL: rating |   SQL: price_inr | pandas: title                                                                     | pandas: category   |   pandas: rating |   pandas: price_inr |
|:----------------------------------------------------------------------------------|:----------------|--------------:|-----------------:|:----------------------------------------------------------------------------------|:-------------------|-----------------:|--------------------:|
| #HigherSelfie: Wake Up Your Life. Free Your Soul. Find Your Tribe.                | Nonfiction      |             5 |          2438.11 | #HigherSelfie: Wake Up Your Life. Free Your Soul. Find Your Tribe.                | Nonfiction         |                5 |             2438.11 |
| Black Dust                                                                        | Romance         |             5 |          3642.91 | Black Dust                                                                        | Romance            |                5 |             3642.91 |
| Chase Me (Paris Nights #2)                                                        | Romance         |             5 |          2665.99 | Chase Me (Paris Nights #2)                                                        | Romance            |                5 |             2665.99 |
| Join                                                                              | Science Fiction |             5 |          3763.19 | Join                                                                              | Science Fiction    |                5 |             3763.19 |
| Princess Between Worlds (Wide-Awake Princess #5)                                  | Fantasy         |             5 |          1407.37 | Princess Between Worlds (Wide-Awake Princess #5)                                  | Fantasy            |                5 |             1407.37 |
| Princess Jellyfish 2-in-1 Omnibus, Vol. 01 (Princess Jellyfish 2-in-1 Omnibus #1) | Sequential Art  |             5 |          1435.86 | Princess Jellyfish 2-in-1 Omnibus, Vol. 01 (Princess Jellyfish 2-in-1 Omnibus #1) | Sequential Art     |                5 |             1435.86 |
| Private Paris (Private #10)                                                       | Fiction         |             5 |          5022.85 | Private Paris (Private #10)                                                       | Fiction            |                5 |             5022.85 |
| Rip it Up and Start Again                                                         | Music           |             5 |          3694.61 | Rip it Up and Start Again                                                         | Music              |                5 |             3694.61 |
| Sapiens: A Brief History of Humankind                                             | History         |             5 |          5721.26 | Sapiens: A Brief History of Humankind                                             | History            |                5 |             5721.26 |
| Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)                           | Sequential Art  |             5 |          5516.6  | Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)                           | Sequential Art     |                5 |             5516.6  |

PASS: pandas.testing.assert_frame_equal confirms identical values and row order.
