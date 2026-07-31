#!/bin/bash
set -e

echo ">>> Acessando pasta do projeto..."
cd /var/www/gerot

echo ">>> Configurando permissões do Git..."
git config --global --add safe.directory /var/www/gerot

echo ">>> Baixando últimas atualizações do GitHub..."
git fetch origin main

echo ">>> Resetando servidor para ficar idêntico ao GitHub..."
git reset --hard origin/main

echo ">>> Ativando ambiente virtual e instalando dependências..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Executando migrações do banco de dados..."
python3 f5db.py

echo ">>> Ajustando permissões de arquivos..."
chown -R root:www-data /var/www/gerot
chmod -R 775 /var/www/gerot

echo ">>> Reiniciando o serviço GEROT..."
systemctl restart transulgerot

echo "=========================================="
echo ">>> 🚀 GEROT ATUALIZADO COM SUCESSO! 🚀"
echo "=========================================="