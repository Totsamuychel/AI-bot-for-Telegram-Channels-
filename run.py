import subprocess
import sys
import time

def main():
    print("🚀 Запуск AutoPoster CMS...")
    
    # Запуск сервера админ панели и бота
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "admin_bot.main:app", "--host", "127.0.0.1", "--port", "8000"]
    )
    
    print("⏳ Ожидание запуска административной панели...")
    time.sleep(3) # Даем боту время поднять базу данных
    
    # Запуск агрегатора новостей
    aggregator_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "news_aggregator.main:app", "--host", "127.0.0.1", "--port", "8001"]
    )

    try:
        print("\n✅ Все сервисы успешно запущены!")
        print("👉 Панель управления доступна по адресу: http://127.0.0.1:8000")
        print("🛑 Для остановки нажмите Ctrl + C")
        
        # Ждем завершения процессов (бесконечно)
        bot_process.wait()
        aggregator_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки (Ctrl+C). Завершение работы...")
        bot_process.terminate()
        aggregator_process.terminate()
        bot_process.wait()
        aggregator_process.wait()
        print("Работа всех сервисов завершена.")

if __name__ == "__main__":
    main()
