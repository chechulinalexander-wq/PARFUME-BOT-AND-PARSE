import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import sys
import io
import time
from datetime import datetime
from urllib.parse import urljoin

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def create_perfume_news_table():
    """Создает таблицу для новостей ароматов"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perfume_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            news_title TEXT NOT NULL,
            news_url TEXT NOT NULL UNIQUE,
            news_date TEXT NOT NULL,
            author TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES randewoo_products(id)
        )
    ''')
    
    # Индекс для быстрого поиска по product_id
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_perfume_news_product_id 
        ON perfume_news(product_id)
    ''')
    
    conn.commit()
    return conn

def parse_date(date_str):
    """
    Парсит дату формата '07/27/25 03:05' в datetime объект
    Возвращает None если не удалось распарсить
    """
    try:
        # Формат: MM/DD/YY HH:MM
        date_obj = datetime.strptime(date_str.strip(), '%m/%d/%y %H:%M')
        return date_obj
    except Exception as e:
        return None

def is_2025(date_obj):
    """Проверяет, что дата относится к 2025 году"""
    if date_obj is None:
        return False
    return date_obj.year == 2025

def parse_perfume_news(scraper, fragrantica_url):
    """
    Парсит новости со страницы аромата на Fragrantica
    Возвращает список новостей за 2025 год
    """
    try:
        response = scraper.get(fragrantica_url, timeout=30)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем все блоки с новостями
        news_blocks = soup.find_all('div', class_='newslist')
        
        news_list = []
        
        for block in news_blocks:
            try:
                # Дата
                date_div = block.find('div', class_='right-bottom-corner-abs')
                if not date_div:
                    continue
                
                date_str = date_div.get_text(strip=True)
                date_obj = parse_date(date_str)
                
                # Проверяем, что дата в 2025 году
                if not is_2025(date_obj):
                    continue
                
                # Заголовок и ссылка
                link = block.find('a', href=lambda x: x and '/news/' in x)
                if not link:
                    continue
                
                h4 = link.find('h4')
                if not h4:
                    continue
                
                title = h4.get_text(strip=True)
                news_url = urljoin('https://www.fragrantica.ru', link['href'])
                
                # Автор
                author = None
                author_tag = block.find('i')
                if author_tag:
                    author = author_tag.get_text(strip=True)
                
                news_list.append({
                    'title': title,
                    'url': news_url,
                    'date': date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    'author': author
                })
                
            except Exception as e:
                continue
        
        return news_list
        
    except Exception as e:
        print(f"  ✗ Ошибка парсинга новостей: {e}")
        return []

def process_all_perfumes():
    """Обрабатывает все ароматы и парсит связанные новости"""
    conn = create_perfume_news_table()
    cursor = conn.cursor()
    
    # Получаем все товары с URL Fragrantica
    cursor.execute('''
        SELECT id, brand, name, fragrantica_url 
        FROM randewoo_products 
        WHERE fragrantica_url IS NOT NULL
        ORDER BY id
    ''')
    products = cursor.fetchall()
    
    if not products:
        print("✓ Нет товаров с URL Fragrantica")
        conn.close()
        return
    
    print(f"\nНайдено ароматов для обработки: {len(products)}\n")
    
    # Создаем scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    # Статистика
    total_news = 0
    products_with_news = 0
    products_without_news = 0
    
    # ПАКЕТНАЯ ОБРАБОТКА
    BATCH_SIZE = 10
    BATCH_PAUSE = 2
    
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(products), BATCH_SIZE):
        batch_products = products[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"{'='*80}")
        print(f"ПАКЕТ {current_batch}/{total_batches} (ароматы {batch_num + 1}-{min(batch_num + BATCH_SIZE, len(products))})")
        print(f"{'='*80}\n")
        
        # Новый scraper для каждого пакета
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        for idx_in_batch, (product_id, brand, name, fragrantica_url) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}")
            
            try:
                # Парсим новости
                news_list = parse_perfume_news(scraper, fragrantica_url)
                
                if news_list:
                    products_with_news += 1
                    print(f"  ✓ Найдено новостей (2025): {len(news_list)}")
                    
                    # Сохраняем в БД
                    added = 0
                    skipped = 0
                    
                    for news in news_list:
                        try:
                            cursor.execute('''
                                INSERT INTO perfume_news (product_id, news_title, news_url, news_date, author)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (product_id, news['title'], news['url'], news['date'], news['author']))
                            added += 1
                        except sqlite3.IntegrityError:
                            skipped += 1
                    
                    conn.commit()
                    total_news += added
                    
                    if added > 0:
                        print(f"    Добавлено: {added}, пропущено (дубликаты): {skipped}")
                        for news in news_list[:3]:  # Показываем первые 3
                            print(f"      - {news['title'][:60]}... ({news['date']})")
                else:
                    products_without_news += 1
                    print(f"  ⊘ Нет новостей за 2025 год")
                
                # Пауза между запросами
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n\n⚠ Прервано пользователем")
                conn.close()
                return
            except Exception as e:
                products_without_news += 1
                print(f"  ✗ Ошибка: {e}")
                time.sleep(0.5)
        
        # ПАУЗА МЕЖДУ ПАКЕТАМИ
        if current_batch < total_batches:
            print(f"\n⏸  Пауза {BATCH_PAUSE} сек перед следующим пакетом...\n")
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ:")
    print(f"  Обработано ароматов: {len(products)}")
    print(f"  С новостями (2025): {products_with_news}")
    print(f"  Без новостей: {products_without_news}")
    print(f"  Всего найдено новостей: {total_news}")
    print(f"{'='*80}")

if __name__ == '__main__':
    print("=== Парсер новостей ароматов Fragrantica (2025) ===\n")
    process_all_perfumes()

