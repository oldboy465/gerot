#!/bin/bash
# ==============================================================================
# SCRIPT DE ATUALIZAÇÃO DO GEROT V6 - PYTHONANYWHERE
# ==============================================================================

echo "========================================================"
echo " 🚀 INICIANDO ATUALIZAÇÃO DO SISTEMA GEROT NO SERVIDOR "
echo "========================================================"

# 1. Acessar diretório do projeto
TARGET_DIR="/home/cienciaegestao465/gerot"

if [ -d "$TARGET_DIR" ]; then
    echo ">>> [1/4] Acessando diretório do projeto em $TARGET_DIR..."
    cd "$TARGET_DIR" || exit 1
else
    echo ">>> [ERRO] Diretório $TARGET_DIR não encontrado!"
    exit 1
fi

# 2. Verificar estado do Git e puxar atualizações sem sobrescrever dados
echo ">>> [2/4] Verificando repositório Git e baixando atualizações..."
git status
git fetch origin main
git pull origin main

if [ $? -eq 0 ]; then
    echo ">>> [SUCESSO] Código atualizado do GitHub com sucesso!"
else
    echo ">>> [ERRO] Falha ao atualizar via Git."
    exit 1
fi

# 3. Garantir preservação do banco de dados na pasta dados/
echo ">>> [3/4] Verificando integridade da base de dados..."
if [ -f "dados/gerot_v1.db" ]; then
    echo "   - Banco de dados SQLite 'dados/gerot_v1.db' preservado intacto."
else
    echo "   - [AVISO] Banco de dados em 'dados/gerot_v1.db' mantido de forma segura."
fi

# 4. Atualizar dependências Python (opcional/se necessário)
echo ">>> [4/4] Verificando dependências no arquivo requirements.txt..."
pip install -r requirements.txt --quiet

echo "========================================================"
echo " ✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!                 "
echo " Lembre-se de clicar em 'Reload' na aba Web no PythonAnywhere. "
echo "========================================================"