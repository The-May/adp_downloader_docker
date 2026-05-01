FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY handler.py .
COPY login.py .
COPY downloader.py .
COPY adp.py .
COPY smb_copy.py .

RUN mkdir -p downloads

EXPOSE 8765

CMD ["python", "handler.py"]
