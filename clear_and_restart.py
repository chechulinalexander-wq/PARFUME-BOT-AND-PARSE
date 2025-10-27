import sqlite3
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*80)
print("ОЧИСТКА БД")
print("="*80 + "\n")

conn = sqlite3.connect('fragrantica_news.db', timeout=30)
cursor = conn.cursor()

# Проверяем текущее состояние
cursor.execute('SELECT COUNT(*) FROM perfume_news')
news_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM randewoo_products')
products_count = cursor.fetchone()[0]

print(f"📊 Текущее состояние:")
print(f"  • Товаров: {products_count}")
print(f"  • Новостей: {news_count}\n")

# Очищаем
print("🗑️  Удаляю данные...")
cursor.execute('DELETE FROM perfume_news')
print(f"  ✓ Удалено {news_count} новостей")

cursor.execute('DELETE FROM randewoo_products')
print(f"  ✓ Удалено {products_count} товаров")

conn.commit()
conn.close()

print("\n✓ БД очищена!")
print("\n💡 Теперь можно запустить:")
print("   python full_parsing_cycle_selenium.py\n")
print("="*80)

