import sqlite3
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*80)
print("СТАТУС БД")
print("="*80 + "\n")

conn = sqlite3.connect('fragrantica_news.db', timeout=30)
cursor = conn.cursor()

# Проверяем товары
cursor.execute('SELECT COUNT(*) FROM randewoo_products')
total_products = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM randewoo_products WHERE fragrantica_url IS NOT NULL')
products_with_fragrantica = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM randewoo_products WHERE fragrantica_url IS NULL')
products_without_fragrantica = cursor.fetchone()[0]

# Проверяем новости
cursor.execute('SELECT COUNT(*) FROM perfume_news')
total_news = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT product_id) FROM perfume_news')
products_with_news = cursor.fetchone()[0]

print(f"📦 ТОВАРЫ:")
print(f"  • Всего в БД: {total_products}")
print(f"  • С Fragrantica URL: {products_with_fragrantica} ({products_with_fragrantica/total_products*100:.1f}%)" if total_products > 0 else "  • С Fragrantica URL: 0")
print(f"  • Без Fragrantica URL: {products_without_fragrantica}")

print(f"\n📰 НОВОСТИ:")
print(f"  • Всего статей: {total_news}")
print(f"  • Ароматов с новостями: {products_with_news}")
print(f"  • Среднее статей на аромат: {total_news/products_with_news:.1f}" if products_with_news > 0 else "  • Среднее статей на аромат: 0")

# Если есть товары без Fragrantica - покажем примеры
if products_without_fragrantica > 0:
    print(f"\n❌ ПРИМЕРЫ ТОВАРОВ БЕЗ FRAGRANTICA (первые 5):")
    cursor.execute('''
        SELECT brand, name 
        FROM randewoo_products 
        WHERE fragrantica_url IS NULL 
        LIMIT 5
    ''')
    for brand, name in cursor.fetchall():
        print(f"  • {brand} - {name}")

# Если есть товары с Fragrantica - покажем примеры
if products_with_fragrantica > 0:
    print(f"\n✅ ПРИМЕРЫ ТОВАРОВ С FRAGRANTICA (первые 5):")
    cursor.execute('''
        SELECT brand, name, fragrantica_url 
        FROM randewoo_products 
        WHERE fragrantica_url IS NOT NULL 
        LIMIT 5
    ''')
    for brand, name, url in cursor.fetchall():
        print(f"  • {brand} - {name}")
        print(f"    {url}")

conn.close()

print("\n" + "="*80)

