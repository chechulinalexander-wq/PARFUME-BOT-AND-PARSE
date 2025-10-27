import sqlite3
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('fragrantica_news.db', timeout=30)
cursor = conn.cursor()

print("="*80)
print("ДЕТАЛЬНАЯ СТАТИСТИКА ПО НОВОСТЯМ")
print("="*80 + "\n")

# 1. Товары С новостями
print("✅ АРОМАТЫ С НОВОСТЯМИ (первые 10):\n")
cursor.execute('''
    SELECT p.brand, p.name, p.fragrantica_url, COUNT(n.id) as news_count
    FROM randewoo_products p
    JOIN perfume_news n ON p.id = n.product_id
    WHERE p.fragrantica_url IS NOT NULL
    GROUP BY p.id
    ORDER BY news_count DESC
    LIMIT 10
''')

for brand, name, url, count in cursor.fetchall():
    print(f"  • {brand} - {name}")
    print(f"    Новостей: {count}")
    print(f"    URL: {url}\n")

# 2. Примеры товаров БЕЗ новостей (популярные бренды)
print("\n" + "="*80)
print("⊘ АРОМАТЫ БЕЗ НОВОСТЕЙ (популярные бренды):\n")
cursor.execute('''
    SELECT p.brand, p.name, p.fragrantica_url
    FROM randewoo_products p
    LEFT JOIN perfume_news n ON p.id = n.product_id
    WHERE p.fragrantica_url IS NOT NULL 
    AND n.id IS NULL
    AND p.brand IN ('Tom Ford', 'Chanel', 'Dior', 'Gucci', 'Versace')
    LIMIT 15
''')

for brand, name, url in cursor.fetchall():
    print(f"  • {brand} - {name}")
    print(f"    URL: {url}\n")

# 3. Статистика по годам
print("\n" + "="*80)
print("📅 СТАТИСТИКА НОВОСТЕЙ ПО ГОДАМ:\n")
cursor.execute('''
    SELECT strftime('%Y', news_date) as year, COUNT(*) as count
    FROM perfume_news
    GROUP BY year
    ORDER BY year DESC
''')

for year, count in cursor.fetchall():
    print(f"  {year}: {count} новостей")

# 4. Примеры новостей
print("\n" + "="*80)
print("📰 ПРИМЕРЫ НОВОСТЕЙ (последние 10):\n")
cursor.execute('''
    SELECT p.brand, p.name, n.news_title, n.news_date
    FROM perfume_news n
    JOIN randewoo_products p ON n.product_id = p.id
    ORDER BY n.parsed_at DESC
    LIMIT 10
''')

for brand, name, title, date in cursor.fetchall():
    print(f"  • {brand} - {name}")
    print(f"    Заголовок: {title[:60]}...")
    print(f"    Дата: {date}\n")

conn.close()

print("="*80)

