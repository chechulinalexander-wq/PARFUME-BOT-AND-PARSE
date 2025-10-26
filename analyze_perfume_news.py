import sqlite3
import sys
import io
import time
from openai import OpenAI

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_config(key):
    """Получает конфигурационный параметр из БД"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def add_analysis_column():
    """Добавляет колонку для результата анализа"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE perfume_news ADD COLUMN article_type TEXT')
        conn.commit()
        print("✓ Колонка article_type добавлена")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("⊘ Колонка article_type уже существует")
        else:
            raise
    
    return conn

def analyze_article_with_gpt(api_key, article_url, brand, perfume_name):
    """
    Анализирует статью через GPT API
    Возвращает: "Про аромат" или "Упоминается"
    """
    
    prompt = f"""Analyze the article at the following link:

{article_url}

Is this article about the fragrance {brand} {perfume_name}, or is it about a different fragrance and {brand} {perfume_name} is just mentioned?

If the article is about our fragrance, return the phrase "Про аромат";
if not, return "Упоминается"."""
    
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a perfume expert analyzing articles. Answer strictly with 'Про аромат' or 'Упоминается'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50
        )
        
        result = response.choices[0].message.content.strip()
        
        # Нормализуем ответ
        if "про аромат" in result.lower():
            return "Про аромат"
        else:
            return "Упоминается"
        
    except Exception as e:
        print(f"    ✗ Ошибка GPT API: {e}")
        return None

def process_all_news():
    """Обрабатывает все новости и анализирует их"""
    
    # Проверяем API ключ
    api_key = get_config('openai_api_key')
    if not api_key:
        print("✗ OpenAI API Key не настроен")
        print("  Запустите: python setup_config.py")
        return
    
    print(f"✓ OpenAI API Key найден\n")
    
    conn = add_analysis_column()
    cursor = conn.cursor()
    
    # Получаем все новости без анализа
    cursor.execute('''
        SELECT pn.id, pn.news_title, pn.news_url, rp.brand, rp.name
        FROM perfume_news pn
        JOIN randewoo_products rp ON pn.product_id = rp.id
        WHERE pn.article_type IS NULL
        ORDER BY pn.id
    ''')
    news_list = cursor.fetchall()
    
    if not news_list:
        print("✓ Все новости уже проанализированы")
        conn.close()
        return
    
    print(f"Найдено новостей для анализа: {len(news_list)}\n")
    
    # Статистика
    pro_aromat = 0
    upominaetsya = 0
    errors = 0
    
    # ПАКЕТНАЯ ОБРАБОТКА
    BATCH_SIZE = 10
    BATCH_PAUSE = 3  # Пауза между пакетами
    REQUEST_PAUSE = 2  # Пауза между запросами
    
    total_batches = (len(news_list) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(news_list), BATCH_SIZE):
        batch_news = news_list[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"{'='*80}")
        print(f"ПАКЕТ {current_batch}/{total_batches} (новости {batch_num + 1}-{min(batch_num + BATCH_SIZE, len(news_list))})")
        print(f"{'='*80}\n")
        
        for idx_in_batch, (news_id, title, url, brand, perfume_name) in enumerate(batch_news, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(news_list)}] {brand} - {perfume_name}")
            print(f"  Новость: {title[:60]}...")
            print(f"  URL: {url}")
            
            try:
                # Анализируем через GPT
                result = analyze_article_with_gpt(api_key, url, brand, perfume_name)
                
                if result:
                    # Сохраняем в БД
                    cursor.execute('''
                        UPDATE perfume_news 
                        SET article_type = ? 
                        WHERE id = ?
                    ''', (result, news_id))
                    conn.commit()
                    
                    print(f"  ✓ Результат: {result}")
                    
                    if result == "Про аромат":
                        pro_aromat += 1
                    else:
                        upominaetsya += 1
                else:
                    errors += 1
                    print(f"  ✗ Ошибка анализа")
                
                # Статистика
                total_processed = pro_aromat + upominaetsya
                if total_processed > 0:
                    print(f"  Статистика: Про аромат: {pro_aromat} | Упоминается: {upominaetsya} | Ошибки: {errors}")
                
                # Пауза между запросами
                time.sleep(REQUEST_PAUSE)
                
            except KeyboardInterrupt:
                print("\n\n⚠ Прервано пользователем")
                conn.close()
                return
            except Exception as e:
                errors += 1
                print(f"  ✗ Ошибка: {e}")
                time.sleep(REQUEST_PAUSE)
        
        # ПАУЗА МЕЖДУ ПАКЕТАМИ
        if current_batch < total_batches:
            print(f"\n⏸  Пауза {BATCH_PAUSE} сек перед следующим пакетом...\n")
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ:")
    print(f"  Всего проанализировано: {len(news_list)}")
    print(f"  Про аромат: {pro_aromat} ({pro_aromat/len(news_list)*100:.1f}%)")
    print(f"  Упоминается: {upominaetsya} ({upominaetsya/len(news_list)*100:.1f}%)")
    print(f"  Ошибки: {errors}")
    print(f"{'='*80}")

if __name__ == '__main__':
    print("=== Анализ статей через GPT ===\n")
    process_all_news()

