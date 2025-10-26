import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_perfume_news():
    """Выводит все новости ароматов из БД"""
    try:
        conn = sqlite3.connect('fragrantica_news.db')
        cursor = conn.cursor()
        
        # Статистика
        cursor.execute('SELECT COUNT(*) FROM perfume_news')
        total_news = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(DISTINCT product_id) 
            FROM perfume_news
        ''')
        products_with_news = cursor.fetchone()[0]
        
        print(f"\n{'='*80}")
        print(f"СТАТИСТИКА:")
        print(f"  Всего новостей (2025): {total_news}")
        print(f"  Ароматов с новостями: {products_with_news}")
        print(f"{'='*80}\n")
        
        if total_news == 0:
            print("База данных пуста")
            return
        
        # Получаем новости с информацией о продукте
        cursor.execute('''
            SELECT 
                pn.id,
                rp.brand,
                rp.name,
                pn.news_title,
                pn.news_url,
                pn.news_date,
                pn.author
            FROM perfume_news pn
            JOIN randewoo_products rp ON pn.product_id = rp.id
            ORDER BY pn.news_date DESC
        ''')
        news = cursor.fetchall()
        
        print(f"=== ВСЕ НОВОСТИ (по дате, новые первые) ===\n")
        
        for news_id, brand, name, title, url, date, author in news:
            print(f"ID: {news_id}")
            print(f"Аромат: {brand} - {name}")
            print(f"Заголовок: {title}")
            print(f"URL: {url}")
            print(f"Дата: {date}")
            print(f"Автор: {author if author else 'N/A'}")
            print("-" * 80)
        
        # Топ ароматов по количеству новостей
        print(f"\n{'='*80}")
        print(f"ТОП-10 АРОМАТОВ ПО КОЛИЧЕСТВУ НОВОСТЕЙ (2025):")
        print(f"{'='*80}\n")
        
        cursor.execute('''
            SELECT 
                rp.brand,
                rp.name,
                COUNT(pn.id) as news_count
            FROM randewoo_products rp
            JOIN perfume_news pn ON rp.id = pn.product_id
            GROUP BY rp.id
            ORDER BY news_count DESC
            LIMIT 10
        ''')
        top_products = cursor.fetchall()
        
        for i, (brand, name, count) in enumerate(top_products, 1):
            print(f"{i}. {brand} - {name}: {count} новостей")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с БД: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    view_perfume_news()

