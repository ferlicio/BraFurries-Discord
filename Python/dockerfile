FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

## RUN mkdir -p /app/data

CMD ["python", "bot.py"]