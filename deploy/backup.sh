#!/bin/sh
# pg_dump diário às 04h (horário do contêiner, UTC) com retenção simples:
# 7 diários + 4 semanais. Offsite: aponte um rclone/rsync para /backups
# do host — o volume é a fonte. Teste de restore: deploy/README.md.
while true; do
  agora=$(date +%H%M)
  if [ "$agora" = "0400" ]; then
    arq="/backups/afilify-$(date +%Y%m%d).sql.gz"
    pg_dump -h db -U afilify afilify | gzip > "$arq" && echo "backup: $arq"
    find /backups -name 'afilify-*.sql.gz' -mtime +7  ! -newermt "$(date -d @$(( $(date +%s) - 2419200 )) 2>/dev/null || date -v-28d +%Y-%m-%d)" -delete 2>/dev/null
    find /backups -name 'afilify-*.sql.gz' -mtime +7 -exec sh -c '
      for f; do d=$(basename "$f" | cut -d- -f2 | cut -c1-8);
      [ "$(date -d "$d" +%u 2>/dev/null || echo 1)" != "1" ] && rm -f "$f"; done' _ {} + 2>/dev/null
    sleep 61
  fi
  sleep 30
done
