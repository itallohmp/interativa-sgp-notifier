FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

WORKDIR /app

# 🔥 Dependências do sistema (ESSENCIAL)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala poetry
RUN pip install --no-cache-dir poetry

# Copia dependências primeiro (cache)
COPY pyproject.toml poetry.lock* /app/

# Configura poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* README.md /app/

# 🔥 Instala dependências
RUN poetry install --no-interaction --no-ansi --no-root

# Copia código depois
COPY . /app

# Porta FastAPI
EXPOSE 8000

# Start
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]