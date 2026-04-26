# 🤖 AI-bot-for-Telegram-Channels (n8n Services)

A comprehensive microservice ecosystem designed for autonomous Telegram channel management. The system automatically fetches news, processes it using Large Language Models (LLM) — either local or via API — and prepares content for publication, including AI-generated imagery.

## 🌟 Concept and Goal
The primary objective of this project is to create a **fully autonomous auto-posting system** for niche Telegram channels. The bot eliminates the need for manual content searching, copywriting, and image selection.

**Workflow:**
1.  **Ingestion (Aggregator):** The system scans RSS feeds and news sources for fresh content.
2.  **Processing (Ollama Service):** An LLM (e.g., Llama 3) analyzes the news, creates a summary tailored to your channel's style, generates a catchy title, and selects relevant hashtags.
3.  **Visualization (Image Service):** A visual prompt is generated, and a unique image is created for the post.
4.  **Management (Admin Bot):** Use a Telegram-based admin interface to monitor the system and manually approve or edit posts before they go live.

---

## 🏗 System Architecture

The project is composed of several independent microservices that can work together via n8n or directly:

*   **`ollama_service` (Port 8000):** The core "brain". It receives raw text and returns a structured JSON containing the post content and an image generation prompt. Powered by local Ollama models.
*   **`image_service` (Port 8001):** Handles visual content generation based on text descriptions.
*   **`news_aggregator` (Port 8002):** A news parser that collects the latest events based on specific topics (AI, Tech, Crypto, etc.).
*   **`admin_bot` (Port 8003):** A Telegram bot for system monitoring and manual post moderation.
*   **`db`:** A PostgreSQL database for storing news history, post status, and configuration.

---

## 🚀 Installation and Setup

### Prerequisites
*   **Docker** and **Docker Compose** installed.
*   (Optional) **Ollama** installed on the host machine if you prefer not to run it inside a container.

### Quick Start
1.  Clone the repository.
2.  Create a `.env` file in the root directory (refer to `.env.example`):
    ```env
    TELEGRAM_TOKEN=your_bot_token
    ADMIN_IDS=12345678,98765432
    ```
3.  Start the entire infrastructure:
    ```bash
    docker-compose up --build -d
    ```
4.  Download the LLM (first run only):
    ```bash
    docker exec -it n8n-services-ollama-1 ollama pull llama3
    ```

---

## 🛠 Usage

### Local Models (Ollama)
By default, the system is configured to use the **Llama 3** model locally. This provides:
*   **Privacy:** Your data never leaves your server.
*   **Zero Cost:** No fees for OpenAI or Anthropic tokens.
*   **Flexibility:** You can easily switch to `mistral`, `gemma`, or any other model from the Ollama library.

### API Integration
Every service provides a REST API, making it easy to integrate into your **n8n** workflows:

1.  **Generate a Post:**
    *   `POST http://localhost:8000/generate_post`
    *   Input: `{ "title": "...", "description": "..." }`
    *   Output: Structured post content with tags.

2.  **Generate an Image:**
    *   `POST http://localhost:8001/generate_image`
    *   Input: `{ "prompt": "..." }`

### Running without Docker (Development)
To run the services directly on your machine:
```bash
pip install -r requirements.txt
python run.py
```

---

## 🎯 Why This Project?
This bot is the ultimate tool for Telegram channel network owners. It allows you to maintain 24/7 activity with high-quality content that is virtually indistinguishable from a human editor's work, while keeping operational costs down to just the electricity for your server.
