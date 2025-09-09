import requests
import time
import sys

# === Configuración ===
SUBDOMAIN_FILE = "subdomain"
LIVE_OUTPUT_FILE = "URLS"
WAYBACK_URL = "https://web.archive.org/cdx/search/cdx"
SLEEP_BETWEEN_ATTEMPTS = 15
MAX_ATTEMPTS = 3

# === Colores ===
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"

def print_banner():
    print(f"""{CYAN}
╔══════════════════════════════════════════════╗
║      🔎 {BOLD}Wayback Recolector de URLs para BBH{RESET}{CYAN}      ║
╚══════════════════════════════════════════════╝
{RESET}""")

def print_result(status, domain, extra=""):
    if status == "ok":
        print(f"{GREEN}[✔] {domain}{RESET} {extra}")
    elif status == "fail":
        print(f"{RED}[✘] {domain}{RESET} {extra}")
    elif status == "retry":
        print(f"{YELLOW}[↻] {domain} → Reintentando...{RESET} {extra}")
    elif status == "start":
        print(f"{BLUE}[➤] {domain}{RESET} {extra}")

def get_wayback_urls(domain):
    params = {
        "url": f"{domain}/*",
        "output": "text",
        "fl": "original",
        "collapse": "urlkey"
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if attempt > 1:
                print_result("retry", domain, f"({attempt}/{MAX_ATTEMPTS}) Esperando {SLEEP_BETWEEN_ATTEMPTS}s")
                time.sleep(SLEEP_BETWEEN_ATTEMPTS)

            response = requests.get(WAYBACK_URL, params=params, timeout=10)
            if response.status_code == 200 and response.text.strip():
                return response.text.splitlines()
        except Exception as e:
            print_result("retry", domain, f"Error: {e}")
            time.sleep(SLEEP_BETWEEN_ATTEMPTS)

    return []

def save_urls(urls):
    with open(LIVE_OUTPUT_FILE, "a") as f:
        for url in urls:
            f.write(url + "\n")

def main():
    print_banner()

    with open(SUBDOMAIN_FILE, "r") as f:
        domains = [line.strip() for line in f if line.strip()]

    total = len(domains)
    url_counter = 0

    for idx, domain in enumerate(domains, 1):
        print_result("start", f"{domain} ({idx}/{total})")
        urls = get_wayback_urls(domain)

        if urls:
            unique_urls = sorted(set(urls))
            save_urls(unique_urls)
            url_counter += len(unique_urls)
            print_result("ok", domain, f"→ {len(unique_urls)} URLs guardadas")
        else:
            print_result("fail", domain, "→ No se encontraron URLs")

        time.sleep(SLEEP_BETWEEN_ATTEMPTS)

    print(f"\n{GREEN}✅ URLs totales guardadas en:{RESET} {BOLD}{LIVE_OUTPUT_FILE}{RESET}")
    print(f"{CYAN}🔢 Total de URLs únicas esta sesión:{RESET} {url_counter}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}⛔ Interrumpido por el usuario.{RESET}")
        sys.exit(1)
