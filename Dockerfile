# Usa a imagem slim do Python
FROM python:3.9-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 1. Instalação das dependências do sistema + COMPILADORES
# Adicionei 'build-essential' e 'python3-dev' para garantir que o pip consiga compilar qualquer coisa
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Configura pasta de trabalho
WORKDIR /app

# 3. Copia os arquivos do projeto
COPY . .

# 4. Instala as bibliotecas do Python
# O --no-cache-dir ajuda a economizar espaço, mas se falhar, o upgrade do pip ajuda
# RUN pip install --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

# 5. Comando para rodar seu app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]