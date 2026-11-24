FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Nombre e icono de la app al instalarla en el móvil
RUN python preparar_web.py

# Render define PORT; main.py lo detecta y arranca como servidor web
CMD ["python", "main.py"]
