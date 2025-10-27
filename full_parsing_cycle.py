import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import io
import time
import unicodedata
import re
from rapidfuzz import fuzz
from datetime import datetime

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# НАСТРОЙКИ
# ============================================================================

MAX_PRODUCTS = 1000  # Максимальное количество товаров для парсинга
CATALOG_URL = 'https://randewoo.ru/category/parfyumeriya'

# ============================================================================
# ШАГ 1: ОЧИСТКА БД
# ============================================================================

def clear_database():
    """Очищает таблицы randewoo_products и perfume_news"""
    print("\n" + "="*80)
    print("ШАГ 1: ОЧИСТКА БД")
    print("="*80 + "\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Удаляем новости
    cursor.execute('SELECT COUNT(*) FROM perfume_news')
    news_count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM perfume_news')
    print(f"✓ Удалено {news_count} записей из perfume_news")
    
    # Удаляем товары
    cursor.execute('SELECT COUNT(*) FROM randewoo_products')
    products_count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM randewoo_products')
    print(f"✓ Удалено {products_count} записей из randewoo_products")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Таблицы очищены")

# ============================================================================
# ШАГ 2: ПАРСИНГ RANDEWOO
# ============================================================================

def parse_randewoo_catalog(max_products=1000):
    """Парсит каталог Randewoo (с лимитом товаров)"""
    print("\n" + "="*80)
    print(f"ШАГ 2: ПАРСИНГ RANDEWOO (лимит: {max_products} товаров)")
    print("="*80 + "\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    all_products = []
    page = 1
    
    print(f"URL: {CATALOG_URL}\n")
    
    while len(all_products) < max_products:
        # ВАЖНО: правильный формат URL для пагинации
        if page == 1:
            page_url = CATALOG_URL
        else:
            page_url = f"{CATALOG_URL}?page={page}"
        
        print(f"Страница {page}: {page_url}")
        
        try:
            time.sleep(3)  # Увеличиваем задержку
            response = scraper.get(page_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = soup.find_all('li', class_='products__item')
            
            if not products:
                print(f"  ⚠ Нет товаров на странице {page}")
                # Проверим статус ответа
                print(f"  Status: {response.status_code}")
                print(f"  Response length: {len(response.text)}")
                if page == 1:
                    print(f"  Первые 500 символов: {response.text[:500]}")
                break
            
            print(f"  Найдено товаров: {len(products)}")
            
            for product in products:
                if len(all_products) >= max_products:
                    break
                
                try:
                    brand_div = product.find('div', class_='b-catalogItem__brand')
                    name_div = product.find('div', class_='b-catalogItem__name')
                    link = product.find('a', class_='b-catalogItem__descriptionLink')
                    
                    if brand_div and name_div and link:
                        brand = brand_div.get_text(strip=True)
                        name = name_div.get_text(strip=True)
                        product_url = urljoin('https://randewoo.ru', link['href'])
                        
                        # Сохраняем в БД сразу
                        cursor.execute('''
                            INSERT OR IGNORE INTO randewoo_products (brand, name, product_url)
                            VALUES (?, ?, ?)
                        ''', (brand, name, product_url))
                        
                        all_products.append({'brand': brand, 'name': name, 'url': product_url})
                        
                except Exception as e:
                    print(f"  ⚠ Ошибка парсинга товара: {e}")
            
            conn.commit()
            print(f"  Всего собрано: {len(all_products)}/{max_products}")
            
            if len(all_products) >= max_products:
                print(f"\n✓ Достигнут лимит в {max_products} товаров")
                break
            
            # Проверяем наличие следующей страницы
            pagination = soup.find('ol', class_='pager')
            if pagination:
                next_link = pagination.find('a', class_='pager__link--forward', attrs={'data-role': 'pagination-next-page'})
                if not next_link:
                    print(f"\n✓ Больше нет страниц")
                    break
            else:
                print(f"\n⚠ Пагинация не найдена")
                break
            
            page += 1
            
        except Exception as e:
            print(f"  ✗ Ошибка загрузки страницы: {e}")
            import traceback
            traceback.print_exc()
            break
    
    conn.close()
    print(f"\n✓ Парсинг завершен: {len(all_products)} товаров")
    return len(all_products)

# ============================================================================
# ШАГ 3: ПОИСК НА FRAGRANTICA
# ============================================================================

def normalize_text(text):
    """Нормализует текст для сравнения"""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = text.strip()
    return text

def search_fragrantica(scraper, brand, name, brand_cache):
    """Ищет аромат на Fragrantica"""
    # Нормализуем бренд для URL
    brand_normalized = normalize_text(brand).replace(' ', '-')
    
    # Формируем URL страницы бренда
    brand_page_url = f"https://www.fragrantica.ru/designers/{brand_normalized}.html"
    
    # Проверяем кэш
    if brand_page_url in brand_cache:
        perfume_links = brand_cache[brand_page_url]
    else:
        # Проверяем существование страницы бренда
        try:
            response = scraper.get(brand_page_url, timeout=30, stream=True)
            status = response.status_code
            response.close()
            
            if status != 200:
                brand_cache[brand_page_url] = []
                return None
        except:
            brand_cache[brand_page_url] = []
            return None
        
        # Парсим страницу бренда
        try:
            time.sleep(1)
            response = scraper.get(brand_page_url, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            perfume_links_raw = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
            perfume_links = []
            
            for plink in perfume_links_raw:
                purl = urljoin('https://www.fragrantica.ru', plink.get('href'))
                ptext = plink.get_text(strip=True)
                perfume_links.append({'url': purl, 'text': ptext})
            
            brand_cache[brand_page_url] = perfume_links
        except:
            brand_cache[brand_page_url] = []
            return None
    
    # Поиск совпадения
    name_normalized = normalize_text(name)
    name_lower = name.lower().strip()
    result_url = None
    best_match_score = 0
    
    for perfume in perfume_links:
        purl = perfume['url']
        ptext = perfume['text']
        
        ptext_normalized = normalize_text(ptext)
        ptext_lower = ptext.lower().strip()
        
        # Точное совпадение
        if name_normalized == ptext_normalized:
            return purl
        
        # Fuzzy matching
        fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
        partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
        token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
        
        max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
        
        if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
            result_url = purl
            best_match_score = max_fuzzy_score
        
        # Word matching
        if len(name_normalized) > 5:
            name_words = set(name_lower.split())
            ptext_words = set(ptext_lower.split())
            common_words = name_words & ptext_words
            
            if len(name_words) > 0:
                word_match_ratio = len(common_words) / len(name_words) * 100
                if word_match_ratio > best_match_score and word_match_ratio >= 70:
                    result_url = purl
                    best_match_score = word_match_ratio
    
    return result_url

def match_fragrantica_urls():
    """Находит соответствия на Fragrantica для всех товаров"""
    print("\n" + "="*80)
    print("ШАГ 3: ПОИСК НА FRAGRANTICA")
    print("="*80 + "\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Добавляем колонку если её нет
    try:
        cursor.execute('ALTER TABLE randewoo_products ADD COLUMN fragrantica_url TEXT')
        conn.commit()
    except:
        pass
    
    # Получаем товары без Fragrantica URL
    cursor.execute('SELECT id, brand, name FROM randewoo_products WHERE fragrantica_url IS NULL')
    products = cursor.fetchall()
    
    if not products:
        print("✓ Все товары уже имеют Fragrantica URL")
        conn.close()
        return
    
    print(f"Товаров для обработки: {len(products)}\n")
    
    BATCH_SIZE = 10
    BATCH_PAUSE = 2
    
    found = 0
    not_found = 0
    
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(products), BATCH_SIZE):
        batch_products = products[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"{'='*80}")
        print(f"ПАКЕТ {current_batch}/{total_batches}")
        print(f"{'='*80}\n")
        
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        brand_cache = {}
        
        for idx_in_batch, (product_id, brand, name) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}")
            
            try:
                fragrantica_url = search_fragrantica(scraper, brand, name, brand_cache)
                
                if fragrantica_url:
                    cursor.execute('UPDATE randewoo_products SET fragrantica_url = ? WHERE id = ?', 
                                 (fragrantica_url, product_id))
                    conn.commit()
                    found += 1
                    print(f"  ✓ Найдено: {fragrantica_url}")
                else:
                    not_found += 1
                    print(f"  ✗ Не найдено")
                
                time.sleep(0.5)
                
            except Exception as e:
                not_found += 1
                print(f"  ✗ Ошибка: {e}")
        
        if current_batch < total_batches:
            print(f"\n⏸  Пауза {BATCH_PAUSE} сек...\n")
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ ПОИСКА:")
    print(f"  Найдено: {found} ({found/len(products)*100:.1f}%)")
    print(f"  Не найдено: {not_found}")
    print(f"{'='*80}")

# ============================================================================
# ШАГ 4: ПАРСИНГ НОВОСТЕЙ
# ============================================================================

def parse_perfume_news_article(scraper, product_id, fragrantica_url):
    """Парсит новости для одного аромата"""
    try:
        time.sleep(1)
        response = scraper.get(fragrantica_url, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        news_blocks = soup.find_all('div', class_='newslist')
        
        for block in news_blocks:
            date_div = block.find('div', class_='right-bottom-corner-abs')
            if date_div:
                date_str = date_div.get_text(strip=True)
                try:
                    if len(date_str.split('/')[2].split(' ')[0]) == 2:
                        news_date = datetime.strptime(date_str, '%m/%d/%y %H:%M')
                    else:
                        news_date = datetime.strptime(date_str, '%m/%d/%Y %H:%M')
                    
                    if news_date.year == 2025:
                        title_tag = block.find('h4')
                        link_tag = block.find('a', href=True)
                        author_tag = block.find('p')
                        
                        if title_tag and link_tag:
                            news_title = title_tag.get_text(strip=True)
                            news_url = urljoin('https://www.fragrantica.ru', link_tag['href'])
                            author = author_tag.get_text(strip=True).replace('от', '').strip() if author_tag else None
                            
                            news_list.append({
                                'product_id': product_id,
                                'news_title': news_title,
                                'news_url': news_url,
                                'news_date': news_date,
                                'author': author
                            })
                except ValueError:
                    continue
        
        return news_list
    except Exception as e:
        print(f"    ✗ Ошибка парсинга новостей: {e}")
        return []

def parse_all_news():
    """Парсит новости для всех ароматов"""
    print("\n" + "="*80)
    print("ШАГ 4: ПАРСИНГ НОВОСТЕЙ")
    print("="*80 + "\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Получаем товары с Fragrantica URL
    cursor.execute('''
        SELECT id, brand, name, fragrantica_url 
        FROM randewoo_products 
        WHERE fragrantica_url IS NOT NULL
    ''')
    products = cursor.fetchall()
    
    if not products:
        print("✗ Нет товаров с Fragrantica URL")
        conn.close()
        return
    
    print(f"Товаров для парсинга новостей: {len(products)}\n")
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    total_news = 0
    products_with_news = 0
    
    for idx, (product_id, brand, name, fragrantica_url) in enumerate(products, 1):
        print(f"[{idx}/{len(products)}] {brand} - {name}")
        print(f"  URL: {fragrantica_url}")
        
        try:
            news_list = parse_perfume_news_article(scraper, product_id, fragrantica_url)
            
            if news_list:
                for news in news_list:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO perfume_news 
                            (product_id, news_title, news_url, news_date, author)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (news['product_id'], news['news_title'], news['news_url'], 
                              news['news_date'], news['author']))
                    except:
                        pass
                
                conn.commit()
                total_news += len(news_list)
                products_with_news += 1
                print(f"  ✓ Найдено новостей: {len(news_list)}")
            else:
                print(f"  ⊘ Новостей не найдено")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ ПАРСИНГА НОВОСТЕЙ:")
    print(f"  Всего новостей: {total_news}")
    print(f"  Ароматов с новостями: {products_with_news}/{len(products)}")
    print(f"{'='*80}")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    print("\n" + "="*80)
    print("ГЛОБАЛЬНЫЙ ПАРСИНГ - ПОЛНЫЙ ЦИКЛ")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Шаг 1: Очистка
        clear_database()
        
        # Шаг 2: Парсинг Randewoo
        products_count = parse_randewoo_catalog(MAX_PRODUCTS)
        
        if products_count == 0:
            print("\n✗ Товары не найдены, парсинг остановлен")
            return
        
        # Шаг 3: Поиск на Fragrantica
        match_fragrantica_urls()
        
        # Шаг 4: Парсинг новостей
        parse_all_news()
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print("ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН!")
        print(f"Время выполнения: {elapsed/60:.1f} минут")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Прервано пользователем")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

