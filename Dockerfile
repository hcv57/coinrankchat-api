FROM python:alpine

WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY coinrankchat coinrankchat

FROM python:alpine

WORKDIR /usr/src/app
RUN apk add --no-cache git
RUN pip install --no-cache-dir gunicorn git+https://github.com/hcv57/coinrankchat-api#egg=coinrankchat_api
EXPOSE 8000
CMD ["gunicorn", "-w 3", "-b 0.0.0.0", "coinrankchat.web:app"]