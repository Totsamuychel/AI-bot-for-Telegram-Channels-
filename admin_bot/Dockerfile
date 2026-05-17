FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv/admin_bot/

EXPOSE 8000

CMD ["uvicorn", "admin_bot.main:app", "--host", "0.0.0.0", "--port", "8000"]
