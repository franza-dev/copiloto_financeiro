#!/usr/bin/env bash
# Deploy do Copiloto Financeiro na VPS.
# Uso: ./deploy.sh
#
# Requisitos:
#   - git push já feito para origin/main
#   - chave SSH (~/.ssh/id_ed25519) instalada em root@185.139.1.136
#
# O que faz:
#   1. Puxa o commit mais recente de main na VPS
#   2. Rebuilda as imagens Docker (api + frontend)
#   3. Recria os containers com a nova imagem
#   4. Mostra status + últimas linhas dos logs pra você confirmar que subiu

set -euo pipefail

VPS_HOST="root@185.139.1.136"
VPS_PATH="/root/copiloto_financeiro"

echo "==> Verificando sincronia com o remoto..."
git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "⚠️  Seu HEAD local ($LOCAL) não é o mesmo do origin/main ($REMOTE)."
  echo "    Rode 'git push' antes de deployar, ou cancele com Ctrl+C."
  read -p "    Continuar mesmo assim? [y/N] " -n 1 -r
  echo
  [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo "==> Conectando em ${VPS_HOST} e atualizando ${VPS_PATH}..."
ssh "$VPS_HOST" bash -se << EOF
set -euo pipefail
cd "$VPS_PATH"

echo "--- git pull ---"
git pull

echo "--- docker compose up -d --build ---"
docker compose up -d --build

echo "--- docker compose ps ---"
docker compose ps

echo "--- últimas linhas dos logs ---"
docker compose logs --tail=10 api frontend
EOF

echo ""
echo "✅ Deploy concluído. Abra o site e dê Ctrl+F5 pra ver as mudanças."
