import requests
import schedule
import time
import sys
import os
import json
from datetime import datetime

# Имя файла для хранения настроек
CONFIG_FILE = 'config.json'

def load_config():
    """Загружает токен и ID чата из файла config.json."""
    if not os.path.exists(CONFIG_FILE):
        return None, None # Файла нет
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            token = config.get('TELEGRAM_BOT_TOKEN')
            chat_id = config.get('TELEGRAM_CHAT_ID')
            if not token or not chat_id:
                return None, None # Данные в файле неполные
            return token, chat_id
    except (json.JSONDecodeError, TypeError):
        return None, None # Файл поврежден или пуст

def save_config(token, chat_id):
    """Сохраняет токен и ID чата в файл config.json."""
    config = {
        'TELEGRAM_BOT_TOKEN': token,
        'TELEGRAM_CHAT_ID': chat_id
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"✅ Данные сохранены в файл '{CONFIG_FILE}'.")

def initial_setup():
    """Проводит первоначальную настройку, запрашивая данные у пользователя."""
    print("--- Первоначальная настройка бота ---")
    token = input("Введите токен вашего Telegram бота: ").strip()
    chat_id = input("Введите ваш Chat ID в Telegram: ").strip()
    
    if not token or not chat_id:
        print("❌ Токен и Chat ID не могут быть пустыми. Завершение работы.")
        sys.exit(1)
        
    save_config(token, chat_id)
    return token, chat_id

def get_dollar_to_ruble_rate():
    """Получает актуальный курс доллара к рублю от ЦБ РФ."""
    try:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
        response.raise_for_status()
        data = response.json()
        usd_rate = data['Valute']['USD']['Value']
        return f"{usd_rate:.2f}"
    except Exception as e:
        print(f"Ошибка при получении курса доллара: {e}")
        return "не удалось получить"

def get_crypto_prices():
    """Получает актуальные курсы Биткоина и Эфира в долларах."""
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd')
        response.raise_for_status()
        data = response.json()
        btc_price = data['bitcoin']['usd']
        eth_price = data['ethereum']['usd']
        return f"{btc_price:,.2f}", f"{eth_price:,.2f}"
    except Exception as e:
        print(f"Ошибка при получении курсов криптовалют: {e}")
        return "не удалось получить", "не удалось получить"

def send_telegram_message(message, token, chat_id):
    """Отправляет сообщение в указанный чат Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Сообщение успешно отправлено в Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка при отправке сообщения: {e}")

def send_currency_report(token, chat_id):
    """Основная задача: собирает курсы и инициирует отправку отчета."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Выполняется задача по расписанию: сбор курсов...")
    
    dollar_rate = get_dollar_to_ruble_rate()
    btc_price_usd, eth_price_usd = get_crypto_prices()
    
    message_text = (
        f"☀️ *Ежедневная сводка курсов*\n\n"
        f"🇷🇺 **Доллар к рублю (USD/RUB):** {dollar_rate} ₽\n\n"
        f"📈 *Криптовалюты:*\n"
        f"💰 **Bitcoin (BTC/USD):** ${btc_price_usd}\n"
        f"💎 **Ethereum (ETH/USD):** ${eth_price_usd}"
    )
    
    send_telegram_message(message_text, token, chat_id)

if __name__ == "__main__":
    # 1. Попытка загрузить конфигурацию
    bot_token, chat_id = load_config()
    
    # 2. Если конфигурации нет, запустить первоначальную настройку
    if not bot_token or not chat_id:
        print("Конфигурационный файл не найден или некорректен.")
        bot_token, chat_id = initial_setup()
    else:
        print(f"Конфигурация успешно загружена из '{CONFIG_FILE}'.")
        
    print("Бот запущен. Ожидание запланированного времени для отправки (09:00)...")
    
    # 3. Настройка расписания
    schedule.every().day.at("09:00").do(send_currency_report, token=bot_token, chat_id=chat_id)

    # 4. Бесконечный цикл для работы в фоне
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nБот остановлен вручную.")
        sys.exit(0)
