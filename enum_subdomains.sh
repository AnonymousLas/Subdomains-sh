#!/bin/bash

# Nombre del dominio a buscar
DOMAIN=$1
if [ -z "$DOMAIN" ]; then
    echo "Por favor, ingresa un dominio."
    exit 1
fi

# Crear directorio para los resultados
RESULTS_DIR="enum_$DOMAIN"
mkdir -p $RESULTS_DIR

# Paso 1: Buscar subdominios con subfinder
echo "[+] Buscando subdominios con subfinder..."
subfinder -d $DOMAIN -o $RESULTS_DIR/subdomains.txt
sleep 5  # Añadir un tiempo de espera para no sobrecargar la web

# Paso 2: Buscar más subdominios con assetfinder
echo "[+] Buscando subdominios con assetfinder..."
assetfinder --subs-only $DOMAIN >> $RESULTS_DIR/subdomains.txt
sleep 5  # Tiempo de espera para evitar bloqueos

# Paso 3: Fuzzing con dnsx para encontrar más subdominios
echo "[+] Haciendo fuzzing activo con dnsx..."
dnsx -l $RESULTS_DIR/subdomains.txt -silent >> $RESULTS_DIR/fuzzed_subdomains.txt
sleep 5  # Pausa entre pasos

# Paso 4: Unificar y limpiar resultados
echo "[+] Unificando y limpiando resultados..."
sort -u $RESULTS_DIR/subdomains.txt $RESULTS_DIR/fuzzed_subdomains.txt > $RESULTS_DIR/cleaned_subdomains.txt
sleep 5  # Evitar exceso de peticiones

# Paso 5: Ejecutando HTTPX para obtener códigos de estado
echo "[+] Ejecutando HTTPX para ver status codes..."
httpx -l $RESULTS_DIR/cleaned_subdomains.txt -status-code -o $RESULTS_DIR/httpx_output.txt
sleep 5  # Pausa para evitar bloqueos

# Paso 6: Detectando URLs con status 403
echo "[+] Detectando URLs con status 403..."
grep "403" $RESULTS_DIR/httpx_output.txt > $RESULTS_DIR/403_urls.txt
sleep 5  # Evitar hacer demasiadas peticiones rápidamente

# Paso 7: Intentando bypass de 403 con headers personalizados
echo "[+] Intentando bypass de 403 con headers..."
while read -r url; do
    httpx -url $url -head -status-code -follow-redirects -o $RESULTS_DIR/bypass_403_success.txt
    sleep 5  # Pausa después de cada solicitud
done < $RESULTS_DIR/403_urls.txt

echo "[+] Todo listo. Los resultados han sido guardados en el directorio: $RESULTS_DIR"
