#!/usr/bin/env bash
# Prepara a VM (Ubuntu 24.04) com PostgreSQL e carrega o banco devops_pulse.
# NÃO é para entregar — é só para você montar o ambiente e tirar os prints.
#
# Uso (na VM, com os .sql na mesma pasta):
#   scp -i chave.pem 01_script_create_insert.sql 02_consultas_select.sql setup_vm.sh ubuntu@<IP>:~
#   ssh -i chave.pem ubuntu@<IP>
#   bash setup_vm.sh 'SuaSenhaForte'
set -euo pipefail

SENHA="${1:?Informe a senha do usuário postgres: bash setup_vm.sh 'SuaSenha'}"

echo ">> Instalando PostgreSQL..."
sudo apt-get update -y
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

echo ">> Definindo senha do usuário postgres (usada pelo dashboard via túnel SSH)..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '${SENHA}';"

echo ">> Criando o banco e carregando tabelas + dados..."
cp 01_script_create_insert.sql 02_consultas_select.sql /tmp/
sudo -u postgres psql -c "DROP DATABASE IF EXISTS devops_pulse;"
sudo -u postgres psql -c "CREATE DATABASE devops_pulse;"
sudo -u postgres psql -v ON_ERROR_STOP=1 -d devops_pulse -f /tmp/01_script_create_insert.sql

echo
echo "Pronto. Prints sugeridos (nesta ordem):"
echo "  1) sudo systemctl status postgresql"
echo "  2) sudo -u postgres psql -c 'SELECT version();'"
echo "  3) sudo -u postgres psql -c '\\l'"
echo "  4) sudo -u postgres psql -d devops_pulse -c '\\dt'"
echo "  5) sudo -u postgres psql -d devops_pulse -c '\\d execucao_pipeline'"
echo "  6) sudo -u postgres psql -d devops_pulse -f /tmp/02_consultas_select.sql"
