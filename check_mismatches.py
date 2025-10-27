import sqlite3
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('fragrantica_news.db', timeout=30)
cursor = conn.cursor()

print("="*80)
print("ПРОВЕРКА ВОЗМОЖНЫХ ОШИБОК В СООТВЕТСТВИЯХ")
print("="*80 + "\n")

# Ищем подозрительные несовпадения
print("🔍 ПРОВЕРЯЮ ПОПУЛЯРНЫЕ АРОМАТЫ:\n")

test_cases = [
    ("Chanel", "No5", "No-5"),
    ("Chanel", "Coco Mademoiselle", "Coco-Mademoiselle"),
    ("Tom Ford", "Lost Cherry", "Lost-Cherry"),
    ("Tom Ford", "Tobacco Vanille", "Tobacco-Vanille"),
    ("Dior", "Sauvage", "Sauvage"),
]

for brand, name, expected_in_url in test_cases:
    cursor.execute('''
        SELECT brand, name, fragrantica_url
        FROM randewoo_products
        WHERE brand = ? AND name LIKE ?
    ''', (brand, f"%{name}%"))
    
    result = cursor.fetchone()
    
    if result:
        _, _, url = result
        status = "✅" if expected_in_url.lower() in url.lower() else "⚠️ ВОЗМОЖНАЯ ОШИБКА"
        
        print(f"{status} {brand} - {name}")
        print(f"   URL: {url}")
        print(f"   Ожидается в URL: {expected_in_url}\n")
    else:
        print(f"⊘ {brand} - {name}: НЕ НАЙДЕН В БД\n")

# Статистика по новостям
print("\n" + "="*80)
print("📊 СТАТИСТИКА ПО БРЕНДАМ (топ-10 по количеству товаров):\n")

cursor.execute('''
    SELECT 
        p.brand,
        COUNT(DISTINCT p.id) as total_products,
        COUNT(DISTINCT CASE WHEN p.fragrantica_url IS NOT NULL THEN p.id END) as with_fragrantica,
        COUNT(DISTINCT n.product_id) as with_news
    FROM randewoo_products p
    LEFT JOIN perfume_news n ON p.id = n.product_id
    GROUP BY p.brand
    ORDER BY total_products DESC
    LIMIT 10
''')

for brand, total, with_frag, with_news in cursor.fetchall():
    frag_percent = (with_frag / total * 100) if total > 0 else 0
    news_percent = (with_news / with_frag * 100) if with_frag > 0 else 0
    
    print(f"{brand}:")
    print(f"   Товаров: {total}")
    print(f"   С Fragrantica: {with_frag} ({frag_percent:.1f}%)")
    print(f"   С новостями: {with_news} ({news_percent:.1f}% от найденных)\n")

conn.close()

print("="*80)

