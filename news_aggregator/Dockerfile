FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv/news_aggregator/

EXPOSE 8002

CMD ["uvicorn", "news_aggregator.main:app", "--host", "0.0.0.0", "--port", "8002"]
