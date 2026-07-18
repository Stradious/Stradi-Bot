FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN useradd --create-home botuser
RUN mkdir -p /app/data && chown -R botuser:botuser /app/data
USER botuser

CMD ["python", "main.py"]
