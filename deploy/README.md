# Deploy na VPS (KVM 1)

## Uma vez
```bash
# na VPS (Ubuntu 24.04)
curl -fsSL https://get.docker.com | sh
git clone git@github.com:juliowcezar22-wq/afilify.git /opt/afilify
cd /opt/afilify && cp deploy/exemplo.env deploy/.env   # preencher
scp .mlcookie vps:/opt/afilify/.mlcookie && chmod 600 /opt/afilify/.mlcookie
```

## Imagem do painel — SEMPRE buildar fora da VPS (1 vCPU)
```bash
# na sua máquina
docker build -f deploy/Dockerfile.painel -t afilify-painel .
docker save afilify-painel | gzip | ssh vps 'gunzip | docker load'
```

## Subir / atualizar
```bash
cd /opt/afilify && git pull
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build worker
```

## Migrar os dados do Mac (cutover)
```bash
scp dados/ofertas.db vps:/opt/afilify/dados/
docker compose ... run --rm worker python db/importar_sqlite.py dados/ofertas.db
```

## Teste de restore (fazer 1x por mês — backup sem restore testado não é backup)
```bash
docker compose ... exec db createdb -U afilify ensaio
gunzip -c /var/lib/docker/volumes/deploy_backups/_data/afilify-XXXX.sql.gz \
  | docker compose ... exec -T db psql -U afilify ensaio
docker compose ... exec db psql -U afilify ensaio -c 'SELECT COUNT(*) FROM ofertas'
docker compose ... exec db dropdb -U afilify ensaio
```
