FROM python:3.11.2

RUN apt-get update

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload", "--port", "8000"]