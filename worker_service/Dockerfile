FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv/worker_service/

EXPOSE 8010

CMD ["uvicorn", "worker_service.main:app", "--host", "0.0.0.0", "--port", "8010"]
