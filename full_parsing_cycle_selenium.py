import sqlite3
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import io
import time
import unicodedata
import re
from rapidfuzz import fuzz
from datetime import datetime
import cloudscraper
import warnings

# Подавляем предупреждения
warnings.filterwarnings('ignore')

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# НАСТРОЙКИ
# ============================================================================

MAX_PRODUCTS = 1000
CATALOG_URL = 'https://randewoo.ru/category/parfyumeriya'

# ============================================================================
# НАСТРОЙКИ SMARTPROXY
# ============================================================================

SMARTPROXY_HOST = "proxy.smartproxy.net"
SMARTPROXY_PORT = 3120
SMARTPROXY_USER = "smart-qad2gx6xmehj"
SMARTPROXY_PASS = "twYMsn3pEJ4DqZqk"

# Формируем URL прокси
PROXY_URL = f"http://{SMARTPROXY_USER}:{SMARTPROXY_PASS}@{SMARTPROXY_HOST}:{SMARTPROXY_PORT}"

# ============================================================================
# ШАГ 1: ОЧИСТКА БД
# ============================================================================

def clear_database():
    """Очищает таблицы randewoo_products и perfume_news"""
    print("\n" + "="*80, flush=True)
    print("ШАГ 1: ОЧИСТКА БД", flush=True)
    print("="*80 + "\n", flush=True)
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM perfume_news')
    news_count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM perfume_news')
    print(f"✓ Удалено {news_count} записей из perfume_news")
    
    cursor.execute('SELECT COUNT(*) FROM randewoo_products')
    products_count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM randewoo_products')
    print(f"✓ Удалено {products_count} записей из randewoo_products")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Таблицы очищены")

# ============================================================================
# ШАГ 2: ПАРСИНГ RANDEWOO С SELENIUM
# ============================================================================

def parse_randewoo_with_selenium(max_products=1000):
    """Парсит каталог Randewoo используя Selenium"""
    print("\n" + "="*80, flush=True)
    print(f"ШАГ 2: ПАРСИНГ RANDEWOO (лимит: {max_products} товаров)", flush=True)
    print("="*80 + "\n", flush=True)
    
    conn = sqlite3.connect('fragrantica_news.db', timeout=30)
    cursor = conn.cursor()
    
    # Проверяем текущее состояние БД
    cursor.execute('SELECT COUNT(*) FROM randewoo_products')
    existing_count = cursor.fetchone()[0]
    print(f"📊 Товаров в БД: {existing_count}", flush=True)
    
    if existing_count >= max_products:
        print(f"✓ Лимит уже достигнут ({existing_count}/{max_products})")
        conn.close()
        return existing_count
    
    # Настройки Chrome
    options = uc.ChromeOptions()
    options.headless = True  # Без GUI
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    print("⏳ Инициализация Chrome (может занять 10-20 сек)...", flush=True)
    print("   (Скачивание драйвера при первом запуске...)", flush=True)
    
    driver = uc.Chrome(options=options, version_main=None)
    
    print("✓ Chrome запущен!", flush=True)
    
    all_products = []
    page = 1
    
    try:
        while len(all_products) < max_products:
            if page == 1:
                page_url = CATALOG_URL
            else:
                page_url = f"{CATALOG_URL}?page={page}"
            
            print(f"\nСтраница {page}: {page_url}", flush=True)
            
            try:
                print("  🌐 Загружаю страницу...", end=" ", flush=True)
                driver.get(page_url)
                print("✓", flush=True)
                
                # На первой странице добавляем параметр сортировки в URL и перезагружаем
                if page == 1:
                    print("  🔽 Применяю сортировку по отзывам...", end=" ", flush=True)
                    
                    # Переходим на URL с сортировкой
                    sorted_url = f"{CATALOG_URL}?sorting=comments_count"
                    driver.get(sorted_url)
                    
                    print("✓", flush=True)
                    print("  ⏳ Ждем загрузки отсортированных товаров (10 сек)...", end=" ", flush=True)
                    time.sleep(10)
                    print("✓", flush=True)
                else:
                    print("  ⏳ Ждем загрузки JS (8 сек)...", end=" ", flush=True)
                    time.sleep(8)
                    print("✓", flush=True)
                
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                products = soup.find_all('li', class_='products__item')
                
                if not products:
                    print(f"  ⚠ Нет товаров на странице {page}")
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
                            
                            cursor.execute('''
                                INSERT OR IGNORE INTO randewoo_products (brand, name, product_url)
                                VALUES (?, ?, ?)
                            ''', (brand, name, product_url))
                            
                            all_products.append({'brand': brand, 'name': name, 'url': product_url})
                            
                            # Показываем каждый товар
                            print(f"  [{len(all_products)}/{max_products}] {brand} - {name}")
                            
                    except Exception as e:
                        print(f"  ⚠ Ошибка парсинга товара: {e}")
                
                conn.commit()
                print(f"  Всего собрано: {len(all_products)}/{max_products}")
                
                if len(all_products) >= max_products:
                    print(f"\n✓ Достигнут лимит в {max_products} товаров")
                    break
                
                # Проверяем пагинацию
                pagination = soup.find('ol', class_='pager')
                if pagination:
                    next_link = pagination.find('a', class_='pager__link--forward')
                    if not next_link:
                        print(f"\n✓ Больше нет страниц")
                        break
                else:
                    print(f"\n⚠ Пагинация не найдена")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  ✗ Ошибка загрузки страницы: {e}")
                break
    
    finally:
        driver.quit()
        conn.close()
    
    print(f"\n✓ Парсинг завершен: {len(all_products)} товаров")
    return len(all_products)

# ============================================================================
# ШАГ 3: ПОИСК НА FRAGRANTICA
# ============================================================================

def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return text.strip()

def search_fragrantica(scraper, brand, name, brand_cache):
    """Проверенная функция поиска из add_fragrantica_url_final.py"""
    
    # Проверяем кеш бренда
    brand_key = brand.lower().strip()
    if brand_key in brand_cache:
        perfume_links = brand_cache[brand_key]
        
        name_normalized = normalize_text(name)
        name_lower = name.lower().strip()
        
        best_match = None
        best_match_score = 0
        
        for plink in perfume_links:
            purl = plink['url']
            ptext = plink['text']
            
            ptext_normalized = normalize_text(ptext)
            ptext_lower = ptext.lower().strip()
            
            if name_normalized == ptext_normalized:
                return purl
            
            fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
            partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
            token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
            
            max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
            
            if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
                best_match = purl
                best_match_score = max_fuzzy_score
            
            if len(name_normalized) > 5:
                name_words = set(name_lower.split())
                ptext_words = set(ptext_lower.split())
                common_words = name_words & ptext_words
                
                if len(name_words) > 0:
                    word_match_ratio = len(common_words) / len(name_words) * 100
                    
                    if word_match_ratio > best_match_score and word_match_ratio >= 70:
                        best_match = purl
                        best_match_score = word_match_ratio
        
        if best_match and best_match_score >= 70:
            return best_match
        
        return None
    
    # Формируем варианты URL страницы бренда
    brand_variants = [
        brand.replace(' ', '-'),
        brand,
    ]
    
    brand_page_url = None
    perfume_links = []
    
    for brand_variant in brand_variants:
        test_url = f"https://www.fragrantica.ru/designers/{brand_variant}.html"
        
        try:
            response = scraper.get(test_url, timeout=10)
            
            if response.status_code == 200:
                brand_page_url = test_url
                break
        except:
            continue
        
        time.sleep(2)  # Пауза между проверками URL бренда
    
    # Парсим страницу бренда
    if brand_page_url:
        try:
            time.sleep(2)  # Пауза перед загрузкой страницы бренда
            response = scraper.get(brand_page_url, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            perfume_links_raw = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
            
            name_normalized = normalize_text(name)
            name_lower = name.lower().strip()
            result_url = None
            best_match_score = 0
            
            for plink in perfume_links_raw:
                purl = urljoin('https://www.fragrantica.ru', plink.get('href'))
                ptext = plink.get_text(strip=True)
                perfume_links.append({'url': purl, 'text': ptext})
                
                ptext_normalized = normalize_text(ptext)
                ptext_lower = ptext.lower().strip()
                
                if name_normalized == ptext_normalized:
                    result_url = purl
                    break
                
                fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
                partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
                token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
                
                max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
                
                if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
                    result_url = purl
                    best_match_score = max_fuzzy_score
                
                if len(name_normalized) > 5:
                    name_words = set(name_lower.split())
                    ptext_words = set(ptext_lower.split())
                    common_words = name_words & ptext_words
                    
                    if len(name_words) > 0:
                        word_match_ratio = len(common_words) / len(name_words) * 100
                        if word_match_ratio > best_match_score and word_match_ratio >= 70:
                            result_url = purl
                            best_match_score = word_match_ratio
            
            # Кешируем результаты
            brand_cache[brand_key] = perfume_links
            
            if result_url:
                return result_url
        
        except Exception as e:
            pass
    
    # Кешируем пустой результат
    brand_cache[brand_key] = []
    return None

def match_fragrantica_urls():
    print("\n" + "="*80)
    print("ШАГ 3: ПОИСК НА FRAGRANTICA")
    print("="*80 + "\n")
    
    print(f"🌐 Прокси: {SMARTPROXY_HOST}:{SMARTPROXY_PORT}")
    print(f"👤 User: {SMARTPROXY_USER}\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE randewoo_products ADD COLUMN fragrantica_url TEXT')
        conn.commit()
    except:
        pass
    
    cursor.execute('SELECT id, brand, name FROM randewoo_products WHERE fragrantica_url IS NULL')
    products = cursor.fetchall()
    
    if not products:
        print("✓ Все товары уже имеют Fragrantica URL")
        conn.close()
        return
    
    print(f"Товаров для обработки: {len(products)}\n")
    
    BATCH_SIZE = 10
    BATCH_PAUSE = 5  # Увеличена пауза между пакетами
    
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
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        # Настраиваем прокси Smartproxy
        scraper.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        brand_cache = {}
        
        for idx_in_batch, (product_id, brand, name) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}")
            print(f"  🔍 Ищу на Fragrantica...", end=" ", flush=True)
            
            try:
                fragrantica_url = search_fragrantica(scraper, brand, name, brand_cache)
                
                if fragrantica_url:
                    cursor.execute('UPDATE randewoo_products SET fragrantica_url = ? WHERE id = ?', 
                                 (fragrantica_url, product_id))
                    conn.commit()
                    found += 1
                    print(f"✓ Найдено")
                    print(f"     {fragrantica_url}")
                else:
                    not_found += 1
                    print(f"✗ Не найдено")
                
                time.sleep(2)  # Увеличена пауза между запросами
                
            except Exception as e:
                not_found += 1
                print(f"✗ Ошибка: {e}")
        
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

def parse_perfume_news_article(scraper, product_id, fragrantica_url, max_retries=3):
    """
    Парсит новости со страницы аромата с retry логикой
    
    Args:
        scraper: cloudscraper instance
        product_id: ID товара в БД
        fragrantica_url: URL страницы аромата
        max_retries: Количество попыток при ошибке
    
    Returns:
        list: Список новостей или пустой список при ошибке
    """
    
    for attempt in range(max_retries):
        try:
            # Пауза перед запросом (увеличена с 2 до 5 сек)
            time.sleep(5)
            
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
                        
                        # Фильтр по году (можно изменить на >= 2024 для большего охвата)
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
                    except ValueError as e:
                        # Ошибка парсинга даты - пропускаем эту новость
                        continue
            
            return news_list
            
        except (ConnectionError, ConnectionResetError) as e:
            # Ошибка подключения - retry с экспоненциальной задержкой
            if attempt < max_retries - 1:
                wait_time = 10 * (2 ** attempt)  # 10, 20, 40 секунд
                print(f"     ⚠ Ошибка подключения (попытка {attempt + 1}/{max_retries}), жду {wait_time} сек...")
                time.sleep(wait_time)
            else:
                print(f"     ✗ Не удалось загрузить после {max_retries} попыток")
                return []
                
        except Exception as e:
            # Неожиданная ошибка
            print(f"     ✗ Ошибка парсинга: {type(e).__name__}: {str(e)[:100]}")
            return []
    
    return []

def parse_all_news():
    print("\n" + "="*80)
    print("ШАГ 4: ПАРСИНГ НОВОСТЕЙ")
    print("="*80 + "\n")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
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
    
    # Настройки батчей
    BATCH_SIZE = 50  # Обрабатываем по 50 товаров
    BATCH_PAUSE = 60  # Пауза 60 секунд между батчами
    
    total_news = 0
    products_with_news = 0
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(products), BATCH_SIZE):
        batch_products = products[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"\n{'='*80}")
        print(f"БАТЧ {current_batch}/{total_batches} (товары {batch_num + 1}-{min(batch_num + BATCH_SIZE, len(products))})")
        print(f"{'='*80}\n")
        
        # Создаем новый scraper для каждого батча
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        # Настраиваем прокси Smartproxy
        scraper.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        
        for idx_in_batch, (product_id, brand, name, fragrantica_url) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}", flush=True)
            print(f"  🔗 URL: {fragrantica_url}", flush=True)
            print(f"  📰 Парсю новости...", end=" ", flush=True)
            
            try:
                news_list = parse_perfume_news_article(scraper, product_id, fragrantica_url)
                
                if news_list:
                    print(f"✓ Найдено: {len(news_list)}", flush=True)
                    
                    for news in news_list:
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO perfume_news 
                                (product_id, news_title, news_url, news_date, author)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (news['product_id'], news['news_title'], news['news_url'], 
                                  news['news_date'], news['author']))
                            print(f"     • {news['news_title'][:60]}... ({news['news_date'].strftime('%Y-%m-%d')})", flush=True)
                        except Exception as e:
                            print(f"     ⚠ Ошибка сохранения: {e}", flush=True)
                    
                    conn.commit()
                    total_news += len(news_list)
                    products_with_news += 1
                else:
                    print(f"⊘ Новостей нет", flush=True)
                
            except Exception as e:
                print(f"✗ Ошибка: {e}", flush=True)
        
        # Пауза между батчами (кроме последнего)
        if current_batch < total_batches:
            print(f"\n⏸  ПАУЗА {BATCH_PAUSE} СЕК ПЕРЕД СЛЕДУЮЩИМ БАТЧЕМ...\n", flush=True)
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ:")
    print(f"  Всего новостей: {total_news}")
    print(f"  Ароматов с новостями: {products_with_news}/{len(products)}")
    print(f"{'='*80}")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    print("\n" + "="*80, flush=True)
    print("ГЛОБАЛЬНЫЙ ПАРСИНГ - УМНЫЙ РЕЖИМ", flush=True)
    print("="*80, flush=True)
    
    start_time = time.time()
    
    try:
        # ============================================================
        # ШАГ 0: АНАЛИЗ СОСТОЯНИЯ БД
        # ============================================================
        print("\n" + "="*80, flush=True)
        print("ШАГ 0: АНАЛИЗ БД", flush=True)
        print("="*80 + "\n", flush=True)
        
        conn = sqlite3.connect('fragrantica_news.db', timeout=30)
        cursor = conn.cursor()
        
        # Проверяем количество товаров
        cursor.execute('SELECT COUNT(*) FROM randewoo_products')
        total_products = cursor.fetchone()[0]
        
        # Проверяем количество товаров с Fragrantica URL
        cursor.execute('SELECT COUNT(*) FROM randewoo_products WHERE fragrantica_url IS NOT NULL')
        products_with_fragrantica = cursor.fetchone()[0]
        
        # Проверяем количество новостей
        cursor.execute('SELECT COUNT(*) FROM perfume_news')
        total_news = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"📊 Текущее состояние БД:")
        print(f"  • Товаров в БД: {total_products}")
        print(f"  • С Fragrantica URL: {products_with_fragrantica}")
        print(f"  • Новостей в БД: {total_news}\n")
        
        # ============================================================
        # ПРИНИМАЕМ РЕШЕНИЕ О ПЛАНЕ ДЕЙСТВИЙ
        # ============================================================
        
        if total_products == 0:
            print("📋 ПЛАН: ПОЛНЫЙ ЦИКЛ (БД пустая)")
            print("  1. ✓ Парсинг Randewoo")
            print("  2. ✓ Поиск на Fragrantica")
            print("  3. ✓ Парсинг новостей\n")
            
            products_count = parse_randewoo_with_selenium(MAX_PRODUCTS)
            
            if products_count == 0:
                print("\n✗ Товары не найдены")
                return
            
            match_fragrantica_urls()
            parse_all_news()
            
        elif products_with_fragrantica == 0:
            print("📋 ПЛАН: ПОИСК FRAGRANTICA + НОВОСТИ")
            print("  1. ⊘ Парсинг Randewoo (пропущен - товары есть)")
            print("  2. ✓ Поиск на Fragrantica")
            print("  3. ✓ Парсинг новостей\n")
            
            match_fragrantica_urls()
            parse_all_news()
            
        elif products_with_fragrantica < total_products:
            print("📋 ПЛАН: ДОГРУЗКА FRAGRANTICA + НОВОСТИ")
            print("  1. ⊘ Парсинг Randewoo (пропущен)")
            print("  2. ✓ Поиск на Fragrantica (только для не найденных)")
            print("  3. ✓ Парсинг новостей\n")
            
            match_fragrantica_urls()
            parse_all_news()
            
        else:
            print("📋 ПЛАН: ТОЛЬКО НОВОСТИ")
            print("  1. ⊘ Парсинг Randewoo (пропущен)")
            print("  2. ⊘ Поиск на Fragrantica (пропущен - все найдены)")
            print("  3. ✓ Парсинг новостей\n")
            
            parse_all_news()
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print("ЦИКЛ ЗАВЕРШЕН!")
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

