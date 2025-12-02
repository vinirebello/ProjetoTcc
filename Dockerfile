# Usa a imagem slim do Python
FROM python:3.9-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 1. Instala dependências do sistema (Tesseract + Compiladores)
# Mantivemos aquela configuração "blindada" que fizemos antes
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Configura pasta de trabalho no container
WORKDIR /app

# --- AQUI ESTÁ A MUDANÇA CRUCIAL ---

# 3. Copia APENAS o requirements.txt da pasta backend para a raiz do container
COPY backend/requirements.txt .

# 4. Instala as bibliotecas
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copia todo o conteúdo de DENTRO da pasta backend para a raiz do container (/app)
# Assim, o Python vai achar seus arquivos 'api' e 'database'
COPY backend/ .

# -----------------------------------

# 6. Comando para rodar
# ATENÇÃO: Verifique onde está seu arquivo principal.
# Se seu arquivo principal (ex: app.py ou main.py) estiver solto dentro da pasta 'backend', use:
CMD ["gunicorn", "api.api:app", "--bind", "0.0.0.0:10000"]

# Se o arquivo principal estiver dentro da pasta 'api' (ex: backend/api/app.py), use:
# CMD ["gunicorn", "api.app:app", "--bind", "0.0.0.0:10000"]