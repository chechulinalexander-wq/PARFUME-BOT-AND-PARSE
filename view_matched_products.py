import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_matched_products():
    """Выводит товары с найденными URL Fragrantica"""
    try:
        conn = sqlite3.connect('fragrantica_news.db')
        cursor = conn.cursor()
        
        # Статистика
        cursor.execute('SELECT COUNT(*) FROM randewoo_products')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM randewoo_products WHERE fragrantica_url IS NOT NULL')
        matched = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM randewoo_products WHERE fragrantica_url IS NULL')
        not_matched = cursor.fetchone()[0]
        
        print(f"\n{'='*80}")
        print(f"СТАТИСТИКА:")
        print(f"  Всего товаров: {total}")
        print(f"  Найдено на Fragrantica: {matched} ({matched/total*100:.1f}%)")
        print(f"  Не найдено: {not_matched} ({not_matched/total*100:.1f}%)")
        print(f"{'='*80}\n")
        
        # Найденные товары
        print("=== НАЙДЕННЫЕ ТОВАРЫ ===\n")
        cursor.execute('''
            SELECT id, brand, name, product_url, fragrantica_url 
            FROM randewoo_products 
            WHERE fragrantica_url IS NOT NULL
            ORDER BY id
        ''')
        products = cursor.fetchall()
        
        for product in products:
            print(f"ID: {product[0]}")
            print(f"Бренд: {product[1]}")
            print(f"Название: {product[2]}")
            print(f"Randewoo: {product[3]}")
            print(f"Fragrantica: {product[4]}")
            print("-" * 80)
        
        # Не найденные товары
        print("\n=== НЕ НАЙДЕННЫЕ ТОВАРЫ ===\n")
        cursor.execute('''
            SELECT id, brand, name, product_url 
            FROM randewoo_products 
            WHERE fragrantica_url IS NULL
            ORDER BY id
        ''')
        products = cursor.fetchall()
        
        for product in products:
            print(f"ID: {product[0]} | {product[1]} - {product[2]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с БД: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    view_matched_products()

