import sqlite3
import sys
import io
import requests

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

def test_bot_token(bot_token):
    """Тестирует токен бота"""
    print("\n1️⃣ Проверка Bot Token...")
    
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            bot_info = result['result']
            print(f"   ✓ Токен валидный")
            print(f"   Bot: @{bot_info['username']}")
            print(f"   ID: {bot_info['id']}")
            print(f"   Имя: {bot_info['first_name']}")
            return True
        else:
            print(f"   ✗ Невалидный токен: {result.get('description')}")
            return False
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False

def test_channel_access(bot_token, channel_id):
    """Тестирует доступ к каналу"""
    print(f"\n2️⃣ Проверка доступа к каналу: {channel_id}")
    
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    
    try:
        response = requests.post(url, json={"chat_id": channel_id}, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            chat_info = result['result']
            print(f"   ✓ Доступ к каналу есть")
            print(f"   Название: {chat_info.get('title', 'N/A')}")
            print(f"   Тип: {chat_info.get('type', 'N/A')}")
            if 'username' in chat_info:
                print(f"   Username: @{chat_info['username']}")
            return True
        else:
            error_desc = result.get('description', 'Unknown error')
            print(f"   ✗ Нет доступа: {error_desc}")
            
            if "chat not found" in error_desc.lower():
                print("\n   💡 Возможные причины:")
                print("      • Неправильный Channel ID")
                print("      • Для публичного канала используйте: @channelname")
                print("      • Для приватного: -100xxxxxxxxxx")
                print("\n   📝 Как получить правильный ID:")
                print("      1. Перешлите сообщение из канала @userinfobot")
                print("      2. Или используйте @getidsbot")
            elif "forbidden" in error_desc.lower():
                print("\n   💡 Бот не добавлен в канал:")
                print("      1. Зайдите в настройки канала")
                print("      2. Administrators → Add Administrator")
                print("      3. Найдите вашего бота и добавьте")
            
            return False
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False

def test_send_message(bot_token, channel_id):
    """Тестирует отправку сообщения"""
    print("\n3️⃣ Тест отправки сообщения...")
    
    test_message = "🧪 Тестовое сообщение от Fragrantica News Bot\n\nЕсли вы видите это - все работает! ✨"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": channel_id,
            "text": test_message
        }, timeout=10)
        
        result = response.json()
        
        if result.get('ok'):
            message_id = result['result']['message_id']
            print(f"   ✓ Сообщение отправлено успешно!")
            print(f"   Message ID: {message_id}")
            print(f"\n   🎉 ВСЕ РАБОТАЕТ! Можете публиковать новости.")
            return True
        else:
            error_desc = result.get('description', 'Unknown error')
            print(f"   ✗ Не удалось отправить: {error_desc}")
            
            if "have no rights to send a message" in error_desc.lower():
                print("\n   💡 У бота нет прав на отправку:")
                print("      1. Откройте канал → Info → Administrators")
                print("      2. Нажмите на вашего бота")
                print("      3. Включите 'Post messages'")
            
            return False
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False

def main():
    print("="*60)
    print("🔍 ТЕСТ TELEGRAM НАСТРОЕК")
    print("="*60)
    
    # Получаем настройки
    bot_token = get_config('telegram_bot_token')
    channel_id = get_config('telegram_channel_id')
    
    if not bot_token:
        print("\n✗ Telegram Bot Token не настроен")
        print("  Запустите: python setup_config.py")
        return
    
    if not channel_id:
        print("\n✗ Telegram Channel ID не настроен")
        print("  Запустите: python setup_config.py")
        return
    
    print(f"\nBot Token: {bot_token[:10]}...{bot_token[-5:]}")
    print(f"Channel ID: {channel_id}")
    
    # Тесты
    token_ok = test_bot_token(bot_token)
    
    if not token_ok:
        print("\n" + "="*60)
        print("❌ Токен бота невалидный. Проверьте настройки.")
        print("="*60)
        return
    
    access_ok = test_channel_access(bot_token, channel_id)
    
    if not access_ok:
        print("\n" + "="*60)
        print("❌ Нет доступа к каналу. Исправьте настройки выше.")
        print("="*60)
        return
    
    send_ok = test_send_message(bot_token, channel_id)
    
    print("\n" + "="*60)
    if send_ok:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("\nТеперь можете публиковать новости:")
        print("  python publish_news.py <ID>")
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ")
        print("\nИсправьте ошибки выше и повторите тест:")
        print("  python test_telegram.py")
    print("="*60)

if __name__ == '__main__':
    main()



