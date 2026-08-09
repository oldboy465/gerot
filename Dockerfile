# Usa uma imagem oficial e leve do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências do sistema necessárias para compilação (C/C++ para pandas/cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código-fonte da aplicação para o contêiner
COPY . .

# Expõe a porta em que o Flask roda
EXPOSE 5000

# Variável de ambiente padrão
ENV FLASK_ENV=production

# Comando para iniciar o GEROT ao subir o contêiner
CMD ["python", "run.py"]