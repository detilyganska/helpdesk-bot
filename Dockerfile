FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --uid 1000 --create-home user && mkdir -p /app/data && chown -R user:user /app/data 

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt 

COPY . .

USER user 
CMD ["python", "bot.py"]