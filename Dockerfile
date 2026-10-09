# Minimal Python HTTP service. Vita Serverless must attach the NVIDIA GPU/driver.
FROM python:3.11-slim
WORKDIR /app
COPY app.py /app/app.py
ENV PORT=8000
EXPOSE 8000
CMD ["python", "-u", "/app/app.py"]
