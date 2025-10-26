import sqlite3
import sys
import io
import getpass

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def save_config(key, value):
    """Сохраняет конфигурационный параметр"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO config (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (key, value))
    
    conn.commit()
    conn.close()

def get_config(key):
    """Получает конфигурационный параметр"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def show_config():
    """Показывает текущую конфигурацию (скрывая ключи)"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT key, value, updated_at FROM config')
    configs = cursor.fetchall()
    
    if not configs:
        print("⊘ Конфигурация пустая")
    else:
        print("\n=== Текущая конфигурация ===\n")
        for key, value, updated_at in configs:
            # Скрываем ключи, показываем только первые и последние символы
            if 'token' in key.lower() or 'key' in key.lower() or 'api' in key.lower():
                if len(value) > 10:
                    masked_value = f"{value[:4]}...{value[-4:]}"
                else:
                    masked_value = "***"
            else:
                masked_value = value
            
            print(f"{key}: {masked_value}")
            print(f"  Обновлено: {updated_at}")
            print()
    
    conn.close()

def setup():
    """Интерактивная настройка конфигурации"""
    print("=== Настройка конфигурации ===\n")
    print("⚠️  API ключи будут сохранены в базе данных")
    print("⚠️  Убедитесь, что файл БД защищен!\n")
    
    # OpenAI API Key
    print("1. OpenAI API Key")
    print("   Получить можно на: https://platform.openai.com/api-keys")
    openai_key = getpass.getpass("   Введите OpenAI API Key (ввод скрыт): ").strip()
    if openai_key:
        save_config('openai_api_key', openai_key)
        print("   ✓ Сохранено\n")
    else:
        print("   ⊘ Пропущено\n")
    
    # Telegram Bot Token
    print("2. Telegram Bot Token")
    print("   Получить у @BotFather в Telegram")
    tg_token = getpass.getpass("   Введите Telegram Bot Token (ввод скрыт): ").strip()
    if tg_token:
        save_config('telegram_bot_token', tg_token)
        print("   ✓ Сохранено\n")
    else:
        print("   ⊘ Пропущено\n")
    
    # Telegram Channel ID
    print("3. Telegram Channel ID")
    print("   Формат: @channelname или -100xxxxxxxxxx")
    tg_channel = input("   Введите Telegram Channel ID: ").strip()
    if tg_channel:
        save_config('telegram_channel_id', tg_channel)
        print("   ✓ Сохранено\n")
    else:
        print("   ⊘ Пропущено\n")
    
    print("=== Настройка завершена ===")
    show_config()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show_config()
    else:
        setup()



