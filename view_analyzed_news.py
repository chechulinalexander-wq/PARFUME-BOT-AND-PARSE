import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_analyzed_news():
    """Выводит статистику и результаты анализа новостей"""
    try:
        conn = sqlite3.connect('fragrantica_news.db')
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM perfume_news')
        total_news = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM perfume_news WHERE article_type = 'Про аромат'")
        pro_aromat = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM perfume_news WHERE article_type = 'Упоминается'")
        upominaetsya = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM perfume_news WHERE article_type IS NULL")
        not_analyzed = cursor.fetchone()[0]
        
        print(f"\n{'='*80}")
        print(f"ОБЩАЯ СТАТИСТИКА:")
        print(f"{'='*80}")
        print(f"  Всего новостей: {total_news}")
        print(f"  Про аромат: {pro_aromat} ({pro_aromat/total_news*100 if total_news > 0 else 0:.1f}%)")
        print(f"  Упоминается: {upominaetsya} ({upominaetsya/total_news*100 if total_news > 0 else 0:.1f}%)")
        print(f"  Не проанализировано: {not_analyzed}")
        print(f"{'='*80}\n")
        
        # Новости "Про аромат"
        if pro_aromat > 0:
            print(f"{'='*80}")
            print(f"СТАТЬИ ПРО АРОМАТ ({pro_aromat}):")
            print(f"{'='*80}\n")
            
            cursor.execute('''
                SELECT 
                    pn.id,
                    rp.brand,
                    rp.name,
                    pn.news_title,
                    pn.news_url,
                    pn.news_date
                FROM perfume_news pn
                JOIN randewoo_products rp ON pn.product_id = rp.id
                WHERE pn.article_type = 'Про аромат'
                ORDER BY pn.news_date DESC
            ''')
            pro_aromat_news = cursor.fetchall()
            
            for news_id, brand, name, title, url, date in pro_aromat_news:
                print(f"ID: {news_id}")
                print(f"Аромат: {brand} - {name}")
                print(f"Заголовок: {title}")
                print(f"URL: {url}")
                print(f"Дата: {date}")
                print("-" * 80)
        
        # Новости "Упоминается"
        if upominaetsya > 0:
            print(f"\n{'='*80}")
            print(f"СТАТЬИ ГДЕ УПОМИНАЕТСЯ ({upominaetsya}):")
            print(f"{'='*80}\n")
            
            cursor.execute('''
                SELECT 
                    pn.id,
                    rp.brand,
                    rp.name,
                    pn.news_title,
                    pn.news_url,
                    pn.news_date
                FROM perfume_news pn
                JOIN randewoo_products rp ON pn.product_id = rp.id
                WHERE pn.article_type = 'Упоминается'
                ORDER BY pn.news_date DESC
            ''')
            upominaetsya_news = cursor.fetchall()
            
            for news_id, brand, name, title, url, date in upominaetsya_news:
                print(f"ID: {news_id}")
                print(f"Аромат: {brand} - {name}")
                print(f"Заголовок: {title}")
                print(f"URL: {url}")
                print(f"Дата: {date}")
                print("-" * 80)
        
        # Топ ароматов с полноценными статьями
        print(f"\n{'='*80}")
        print(f"ТОП-10 АРОМАТОВ С ПОЛНОЦЕННЫМИ СТАТЬЯМИ:")
        print(f"{'='*80}\n")
        
        cursor.execute('''
            SELECT 
                rp.brand,
                rp.name,
                COUNT(pn.id) as articles_count
            FROM randewoo_products rp
            JOIN perfume_news pn ON rp.id = pn.product_id
            WHERE pn.article_type = 'Про аромат'
            GROUP BY rp.id
            ORDER BY articles_count DESC
            LIMIT 10
        ''')
        top_perfumes = cursor.fetchall()
        
        if top_perfumes:
            for i, (brand, name, count) in enumerate(top_perfumes, 1):
                print(f"{i}. {brand} - {name}: {count} статей")
        else:
            print("  Нет данных")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с БД: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    view_analyzed_news()

