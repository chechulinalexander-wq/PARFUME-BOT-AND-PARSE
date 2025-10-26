import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_products():
    """Выводит все товары из базы данных"""
    try:
        conn = sqlite3.connect('fragrantica_news.db')
        cursor = conn.cursor()
        
        # Получаем все товары
        cursor.execute('SELECT id, brand, name, product_url, parsed_at FROM randewoo_products ORDER BY id')
        products = cursor.fetchall()
        
        if not products:
            print("База данных пуста")
            return
        
        print(f"\n=== Всего товаров в базе: {len(products)} ===\n")
        
        for product in products:
            print(f"ID: {product[0]}")
            print(f"Бренд: {product[1]}")
            print(f"Название: {product[2]}")
            print(f"URL: {product[3]}")
            print(f"Дата парсинга: {product[4]}")
            print("-" * 80)
        
        # Статистика по брендам
        cursor.execute('SELECT brand, COUNT(*) as count FROM randewoo_products GROUP BY brand ORDER BY count DESC LIMIT 10')
        top_brands = cursor.fetchall()
        
        print(f"\n=== Топ-10 брендов ===\n")
        for brand, count in top_brands:
            print(f"{brand}: {count} товаров")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с БД: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    view_products()

