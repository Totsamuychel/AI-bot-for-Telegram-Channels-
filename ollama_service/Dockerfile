FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv/ollama_service/

EXPOSE 8000

CMD ["uvicorn", "ollama_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
