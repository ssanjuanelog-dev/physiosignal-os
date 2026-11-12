FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para MNE y procesamiento de señales
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para caché de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY src/ src/
COPY main.py .
COPY run_api.py .
COPY pyproject.toml .

# Instalar el paquete en modo editable
RUN pip install -e .

# Crear directorios para resultados
RUN mkdir -p results/mixtures results/audit results/reports

# Exponer puerto para la API
EXPOSE 8000

# Comando para ejecutar la API
CMD ["python", "run_api.py"]
