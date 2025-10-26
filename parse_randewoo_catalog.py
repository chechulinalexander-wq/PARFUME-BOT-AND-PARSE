import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import io
import time

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def create_database():
    """Создает базу данных и таблицу для товаров"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS randewoo_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            product_url TEXT NOT NULL UNIQUE,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

def parse_catalog_page(scraper, url, page_num=None):
    """Парсит одну страницу каталога"""
    if page_num:
        page_url = f"{url}?page={page_num}"
    else:
        page_url = url
    
    print(f"Загружаю страницу: {page_url}")
    time.sleep(2)
    
    try:
        response = scraper.get(page_url, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Находим все товары
        products = soup.find_all('li', class_='products__item')
        print(f"  Найдено товаров: {len(products)}")
        
        products_list = []
        
        for product in products:
            try:
                # Бренд
                brand_div = product.find('div', class_='b-catalogItem__brand')
                if not brand_div:
                    continue
                brand = brand_div.get_text(strip=True)
                
                # Название
                name_div = product.find('div', class_='b-catalogItem__name')
                if not name_div:
                    continue
                name = name_div.get_text(strip=True)
                
                # Ссылка
                link = product.find('a', class_='b-catalogItem__descriptionLink')
                if not link or not link.get('href'):
                    continue
                product_url = urljoin('https://randewoo.ru', link['href'])
                
                products_list.append({
                    'brand': brand,
                    'name': name,
                    'product_url': product_url
                })
                
            except Exception as e:
                print(f"  ⚠ Ошибка при парсинге товара: {e}")
                continue
        
        # Проверяем есть ли следующая страница
        has_next = False
        max_pages = 1
        
        # Ищем пагинатор
        pagination = soup.find('ol', class_='pager')
        if pagination:
            # Проверяем наличие кнопки "Вперед"
            next_link = pagination.find('a', class_='pager__link--forward', attrs={'data-role': 'pagination-next-page'})
            if next_link:
                has_next = True
            
            # Определяем максимальное количество страниц
            page_links = pagination.find_all('a', class_='pager__link')
            for link in page_links:
                data_page = link.get('data-page')
                if data_page and data_page.isdigit():
                    max_pages = max(max_pages, int(data_page))
        
        return products_list, has_next, max_pages
        
    except Exception as e:
        print(f"  ✗ Ошибка при загрузке страницы: {e}")
        return [], False, 1

def parse_all_catalog(scraper, base_url):
    """Парсит все страницы каталога"""
    all_products = []
    page = 1
    total_pages = None
    
    while True:
        products, has_next, max_pages = parse_catalog_page(scraper, base_url, page if page > 1 else None)
        
        if total_pages is None and max_pages > 1:
            total_pages = max_pages
            print(f"\n  Обнаружено страниц: {total_pages}\n")
        
        if not products:
            print(f"  ⚠ Нет товаров на странице {page}")
            break
        
        all_products.extend(products)
        print(f"  Прогресс: страница {page}/{total_pages or '?'}, собрано товаров: {len(all_products)}")
        
        if not has_next:
            print("\n  ✓ Достигнута последняя страница")
            break
        
        page += 1
        
        # Защита от бесконечного цикла
        if total_pages and page > total_pages:
            print(f"\n  ✓ Обработаны все {total_pages} страниц")
            break
    
    return all_products

def save_to_database(conn, products_list):
    """Сохраняет товары в базу данных"""
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    
    for product in products_list:
        try:
            cursor.execute('''
                INSERT INTO randewoo_products (brand, name, product_url)
                VALUES (?, ?, ?)
            ''', (product['brand'], product['name'], product['product_url']))
            added += 1
            print(f"✓ Добавлено: {product['brand']} - {product['name']}")
        except sqlite3.IntegrityError:
            skipped += 1
            print(f"⊘ Пропущено (дубликат): {product['brand']} - {product['name']}")
    
    conn.commit()
    return added, skipped

def main():
    print("=== Парсер каталога Randewoo ===\n")
    
    # Создаем БД
    conn = create_database()
    print("✓ База данных создана/открыта\n")
    
    # Создаем scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    # URL каталога
    catalog_url = 'https://randewoo.ru/category/parfyumeriya'
    
    try:
        # Парсим все страницы каталога
        print("Начинаю парсинг каталога...\n")
        products_list = parse_all_catalog(scraper, catalog_url)
        print(f"\n✓ Всего спарсено товаров: {len(products_list)}\n")
        
        if products_list:
            # Сохраняем в БД
            print("Сохранение в базу данных...\n")
            added, skipped = save_to_database(conn, products_list)
            print(f"\n=== Результат ===")
            print(f"Добавлено: {added}")
            print(f"Пропущено (дубликаты): {skipped}")
            print(f"Всего: {len(products_list)}")
        else:
            print("⚠ Товары не найдены")
    
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()

