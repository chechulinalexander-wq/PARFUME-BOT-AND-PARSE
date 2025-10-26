import sqlite3
import sys
import io
import time
from openai import OpenAI
import requests
import json
import os

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROMPT = """Imagine you are the world's best messaging strategist and copywriter, as well as a perfume expert and practicing perfumer. Take a deep breath and, step by step, rewrite this text so it can be posted in a Telegram channel.

CRITICAL REQUIREMENTS:
1. Write ONLY in Russian language (русский язык)
2. Keep the text under 900 characters (including spaces) - this is STRICT
3. Make it concise and focused on the most interesting details

Style guidelines:
- Conversational, warm, feminine voice in first person
- Very short paragraphs (1-2 lines max)
- Add 1-2 gentle sensory details (smells, textures)
- Use 1-2 light rhetorical questions for intimacy
- Emojis: maximum 2-3 per post
- Avoid bureaucratic wording and complicated terms
- End with a soft, engaging question or invitation

Remember: Russian language ONLY. Maximum 900 characters. Focus on emotion and key details, skip minor information."""

def get_config(key):
    """Получает конфигурационный параметр из БД"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_news_by_id(news_id):
    """Получает новость по ID"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, url, news_full, news_rewritten, images FROM news WHERE id = ?', (news_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def save_rewritten_news(news_id, rewritten_text):
    """Сохраняет переписанный текст в БД"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE news SET news_rewritten = ? WHERE id = ?', (rewritten_text, news_id))
    conn.commit()
    conn.close()

def rewrite_with_gpt(text, api_key):
    """Переписывает текст с помощью ChatGPT"""
    print("\n📝 Отправляю текст в ChatGPT...")
    
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        
        rewritten = response.choices[0].message.content
        print("✓ Текст переписан ChatGPT")
        print(f"  Длина: {len(rewritten)} символов")
        
        if len(rewritten) > 1024:
            print("  ⚠ ВНИМАНИЕ: Текст длиннее 1024 символов, будет обрезан для caption")
        elif len(rewritten) > 900:
            print("  ⚠ Текст длиннее рекомендуемых 900 символов")
        
        return rewritten
        
    except Exception as e:
        print(f"✗ Ошибка при обращении к ChatGPT: {e}")
        return None

def publish_to_telegram(text, bot_token, channel_id, image_paths=None):
    """Публикует текст и изображения в Telegram канал"""
    print("\n📤 Публикую в Telegram канал...")
    print(f"   Channel ID: {channel_id}")
    
    # Проверяем наличие изображений
    if image_paths and len(image_paths) > 0:
        existing_images = [img for img in image_paths if os.path.exists(img)]
        
        if existing_images:
            print(f"   📸 Отправляю пост с {len(existing_images)} изображениями...")
            
            # Отправляем media group с текстом внутри
            success = send_media_group_with_caption(bot_token, channel_id, existing_images, text)
            
            if success:
                print(f"   ✓ Пост с изображениями опубликован")
                return True
            else:
                print("   ⚠ Не удалось отправить media group, пробую текст отдельно...")
    
    # Если изображений нет или не удалось отправить, отправляем только текст
    print("   📝 Отправляю текст...")
    return send_text_only(text, bot_token, channel_id)

def send_media_group_with_caption(bot_token, channel_id, photo_paths, caption):
    """Отправляет несколько фото как media group с текстом внутри"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
    
    # Telegram позволяет до 10 медиа в одной группе
    photo_paths = photo_paths[:10]
    
    # Telegram лимит на caption - 1024 символа
    if len(caption) > 1024:
        print(f"      ⚠ Caption слишком длинный ({len(caption)} символов), обрезаю до 1024")
        caption = caption[:1021] + "..."
    
    try:
        # Подготавливаем медиа
        media = []
        files = {}
        
        for i, photo_path in enumerate(photo_paths):
            attach_name = f"photo{i}"
            files[attach_name] = open(photo_path, 'rb')
            
            # Добавляем caption только к первому фото
            if i == 0:
                media.append({
                    "type": "photo",
                    "media": f"attach://{attach_name}",
                    "caption": caption
                })
            else:
                media.append({
                    "type": "photo",
                    "media": f"attach://{attach_name}"
                })
        
        data = {
            'chat_id': channel_id,
            'media': json.dumps(media, ensure_ascii=False)
        }
        
        response = requests.post(url, data=data, files=files, timeout=60)
        
        # Закрываем файлы
        for f in files.values():
            f.close()
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return True
        
        # Показываем ошибку если есть
        try:
            result = response.json()
            error_desc = result.get('description', 'Unknown error')
            print(f"      ✗ Ошибка: {error_desc}")
        except:
            print(f"      ✗ HTTP Error {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"      ✗ Ошибка: {e}")
        # Закрываем файлы в случае ошибки
        for f in files.values():
            if not f.closed:
                f.close()
        return False

def send_text_only(text, bot_token, channel_id):
    """Отправляет только текст без изображений"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Telegram лимит: 4096 символов
    MAX_LENGTH = 4096
    
    # Если текст длиннее лимита, разбиваем на части
    if len(text) > MAX_LENGTH:
        print(f"   ⚠ Текст длинный ({len(text)} символов), разбиваю на части...")
        
        # Разбиваем по абзацам
        parts = []
        current_part = ""
        
        for paragraph in text.split('\n\n'):
            if len(current_part) + len(paragraph) + 2 <= MAX_LENGTH:
                if current_part:
                    current_part += '\n\n'
                current_part += paragraph
            else:
                if current_part:
                    parts.append(current_part)
                current_part = paragraph
        
        if current_part:
            parts.append(current_part)
        
        print(f"   📝 Отправляю {len(parts)} частей...")
        
        # Отправляем все части
        for i, part in enumerate(parts, 1):
            data = {"chat_id": channel_id, "text": part}
            
            try:
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        print(f"      ✓ Часть {i}/{len(parts)} отправлена")
                    else:
                        print(f"      ✗ Ошибка части {i}: {result.get('description')}")
                        return False
                else:
                    print(f"      ✗ HTTP {response.status_code}")
                    return False
                
                # Небольшая задержка между частями
                if i < len(parts):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"      ✗ Ошибка: {e}")
                return False
        
        return True
    
    # Текст нормальной длины, отправляем целиком
    data = {
        "chat_id": channel_id,
        "text": text
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"   ✓ Опубликовано в канал {channel_id}")
                message_id = result['result']['message_id']
                print(f"   Message ID: {message_id}")
                return True
        
        # Если ошибка, показываем детали
        try:
            result = response.json()
            error_description = result.get('description', 'Unknown error')
            error_code = result.get('error_code', response.status_code)
            
            print(f"✗ Telegram API Error {error_code}: {error_description}")
            
            # Подсказки по исправлению
            if "chat not found" in error_description.lower():
                print("\n💡 Решение:")
                print("  1. Проверьте правильность Channel ID")
                print("  2. Для публичного канала: @channelname")
                print("  3. Для приватного канала: -100xxxxxxxxxx")
                print("  4. Получить ID можно через @userinfobot")
            elif "bot was blocked" in error_description.lower() or "forbidden" in error_description.lower():
                print("\n💡 Решение:")
                print("  1. Добавьте бота в канал")
                print("  2. Сделайте бота администратором канала")
                print("  3. Дайте боту право 'Post messages'")
            elif "message is too long" in error_description.lower():
                print("\n💡 Решение:")
                print(f"  Текст слишком длинный ({len(text)} символов)")
                print("  Максимум: 4096 символов")
            
            return False
            
        except:
            print(f"✗ HTTP Error {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Timeout: Telegram API не отвечает")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Проверьте интернет соединение")
        return False
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return False

def process_and_publish(news_id, force_rewrite=False):
    """Обрабатывает и публикует новость"""
    print(f"\n{'='*80}")
    print(f"Обработка новости ID: {news_id}")
    print(f"{'='*80}")
    
    # Проверяем конфигурацию
    openai_key = get_config('openai_api_key')
    tg_token = get_config('telegram_bot_token')
    tg_channel = get_config('telegram_channel_id')
    
    if not openai_key:
        print("✗ OpenAI API Key не настроен. Запустите: python setup_config.py")
        return False
    
    if not tg_token:
        print("✗ Telegram Bot Token не настроен. Запустите: python setup_config.py")
        return False
    
    if not tg_channel:
        print("✗ Telegram Channel ID не настроен. Запустите: python setup_config.py")
        return False
    
    # Получаем новость
    news = get_news_by_id(news_id)
    if not news:
        print(f"✗ Новость с ID {news_id} не найдена")
        return False
    
    news_id, title, url, news_full, news_rewritten, images_json = news
    
    print(f"\n📰 Заголовок: {title}")
    print(f"🔗 URL: {url}")
    
    if not news_full:
        print("✗ Полный текст новости отсутствует в БД")
        return False
    
    print(f"📄 Размер оригинального текста: {len(news_full)} символов")
    
    # Переписываем текст (если нужно)
    if news_rewritten and not force_rewrite:
        print("\n⊘ Переписанный текст уже существует, используем его")
        print("   (Используйте --force для принудительной перезаписи)")
        rewritten_text = news_rewritten
    else:
        rewritten_text = rewrite_with_gpt(news_full, openai_key)
        if not rewritten_text:
            return False
        
        # Сохраняем в БД
        save_rewritten_news(news_id, rewritten_text)
        print("✓ Переписанный текст сохранен в БД")
    
    print(f"📝 Размер переписанного текста: {len(rewritten_text)} символов")
    
    # Парсим изображения
    image_paths = []
    if images_json:
        try:
            image_paths = json.loads(images_json)
            existing = [img for img in image_paths if os.path.exists(img)]
            print(f"📸 Изображений: {len(existing)}/{len(image_paths)}")
        except:
            print("⚠ Ошибка чтения изображений")
    
    # Показываем превью
    print(f"\n{'='*80}")
    print("ПРЕВЬЮ ТЕКСТА ДЛЯ ПУБЛИКАЦИИ:")
    print(f"{'='*80}")
    print(rewritten_text[:500])
    if len(rewritten_text) > 500:
        print(f"\n... (всего {len(rewritten_text)} символов)")
    print(f"{'='*80}")
    
    # Публикуем в Telegram
    success = publish_to_telegram(rewritten_text, tg_token, tg_channel, image_paths)
    
    if success:
        print(f"\n{'='*80}")
        print("✓ УСПЕШНО! Новость опубликована")
        print(f"{'='*80}\n")
        return True
    else:
        print(f"\n{'='*80}")
        print("✗ Ошибка при публикации")
        print(f"{'='*80}\n")
        return False

def main():
    print("=== Публикация новости в Telegram ===\n")
    
    if len(sys.argv) > 1:
        try:
            news_id = int(sys.argv[1])
            force = '--force' in sys.argv
            process_and_publish(news_id, force_rewrite=force)
        except ValueError:
            print("✗ ID должен быть числом")
            print("Использование: python publish_news.py <ID> [--force]")
    else:
        # Интерактивный режим
        try:
            news_id = int(input("Введите ID новости: "))
            process_and_publish(news_id)
        except ValueError:
            print("✗ ID должен быть числом")
        except KeyboardInterrupt:
            print("\n\n⊘ Отменено")

if __name__ == '__main__':
    main()

