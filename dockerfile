FROM python:3.9-slim

WORKDIR /app

# pip -l freeze > requirements.txt
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

## RUN mkdir -p /app/data

CMD ["python", "main.py"]