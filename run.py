import subprocess
import sys
import time
import os

def main():
    print("🚀 Запуск микросервисов n8n (Local Mode)...")

    # Конфигурация портов
    services = [
        {"name": "Ollama Service", "module": "ollama_service.main:app", "port": 8000},
        {"name": "Image Service", "module": "image_service.main:app", "port": 8001},
        {"name": "News Aggregator", "module": "news_aggregator.main:app", "port": 8002},
        {"name": "Admin Bot & Web", "module": "admin_bot.main:app", "port": 8003},
    ]

    processes = []

    try:
        for svc in services:
            print(f"📦 Запуск {svc['name']} на порту {svc['port']}...")
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", svc['module'], "--host", "127.0.0.1", "--port", str(svc['port'])]
            )
            processes.append(proc)
            time.sleep(1) # Небольшая пауза для инициализации

        print("\n✅ Все сервисы запущены!")
        print("🔗 Admin Panel: http://127.0.0.1:8003")
        print("🛑 Нажмите Ctrl+C для остановки всех сервисов")

        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервисов...")
        for proc in processes:
            proc.terminate()
        print("👋 Все процессы завершены.")

if __name__ == "__main__":
    main()
