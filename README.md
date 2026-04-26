# n8n Agent Microservices

This project provides a set of microservices designed to be used by n8n for automated content generation.

## Services

### 1. Ollama Service (Port 8000)
Generates Telegram posts from raw news items using a local LLM via Ollama.

**Endpoint:** `POST /generate_post`

**Request Body:**
```json
{
  "title": "News Title",
  "description": "News Description",
  "url": "https://example.com",
  "source": "Source Name"
}
```

**Response:**
```json
{
  "title": "Engaging Title",
  "body": "Post content...",
  "tags": ["#Tag1", "#Tag2"],
  "image_prompt": "Prompt for image generation"
}
```

### 2. Image Service (Port 8001)
Generates images (currently returns a placeholder/mock URL) based on a text prompt.

**Endpoint:** `POST /generate_image`

**Request:**
```json
{
  "prompt": "Futuristic city"
}
```

**Response:**
```json
{
  "image_url": "https://..."
}
```

### 3. News Aggregator (Port 8002)
Fetches latest tech news from RSS feeds.

**Endpoint:** `GET /news?limit=5&topic=ai`

### 4. Admin Bot
Telegram bot for monitoring (optional). Configure `TELEGRAM_TOKEN` in `.env`.

## Setup

1.  install Docker and Docker Compose.
2.  Copy `.env` from template (created in root) if needed (optional for core services).
3.  Run:
    ```bash
    docker-compose up --build
    ```
4.  Pull the Ollama model (first time only):
    ```bash
    docker exec -it n8n-services-ollama-1 ollama pull llama3
    ```
    *(Note: Replace `n8n-services-ollama-1` with your actual container name if different)*

## n8n Integration
- Use the **HTTP Request** node in n8n.
- Point to `http://host.docker.internal:8000`, `8001`, or `8002` (depending on your network setup).
