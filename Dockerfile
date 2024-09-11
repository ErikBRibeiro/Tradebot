FROM python:3.10-slim

LABEL Maintainer="TradeBot"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir data

EXPOSE 8000

CMD ["python", "main_loop.py"]
