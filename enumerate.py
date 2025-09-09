#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, shutil, subprocess, threading, json, signal, socket
from urllib.parse import urlparse

# -------- colores --------
def tty(): return sys.stdout.isatty()
def c(s, code): return f"\033[{code}m{s}\033[0m" if tty() else s
BOLD=lambda s:c(s,"1"); RED=lambda s:c(s,"31"); GRN=lambda s:c(s,"32")
YEL=lambda s:c(s,"33"); BLU=lambda s:c(s,"34"); CYN=lambda s:c(s,"36")

PORTS = "80,443,8080,8443"
HTTPX_ARGS = [
    "httpx","-silent","-follow-redirects",
    "-status-code","-title","-ip","-ports",PORTS,"-json"
]

stop_flag = False
def handle_sigint(sig, frame):
    global stop_flag
    stop_flag = True
    print(YEL("\n[!] Interrumpido por el usuario"))
signal.signal(signal.SIGINT, handle_sigint)

def truncate(s, n):
    s = (s or "").replace("\r"," ").replace("\n"," ")
    return s if len(s)<=n else s[:n-1]+"…"

def check_deps():
    missing=[]
    for bin in ["subfinder","httpx"]:
        if not shutil.which(bin): missing.append(bin)
    if missing:
        print(RED("[x] Faltan dependencias: ")+", ".join(missing))
        print(YEL("  → Instala en macOS: brew install projectdiscovery/tap/subfinder projectdiscovery/tap/httpx"))
        sys.exit(1)

# --- DNS fallback (cacheado) ---
_dns_cache = {}
socket.setdefaulttimeout(2.5)  # evita bloqueos al resolver
def resolve_ip(host: str) -> str:
    if not host:
        return "-"
    if host in _dns_cache:
        return _dns_cache[host]
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        # prioriza IPv4 si hay
        ipv4 = next((ai[4][0] for ai in infos if ai[0] == socket.AF_INET), None)
        ip = ipv4 or (infos[0][4][0] if infos else None)
        _dns_cache[host] = ip or "-"
        return _dns_cache[host]
    except Exception:
        _dns_cache[host] = "-"
        return "-"

def extract_ip(obj) -> str:
    # httpx moderno: "ip"; variantes: "a" (lista)
    ip = obj.get("ip")
    if ip and isinstance(ip, str) and ip.strip():
        return ip.strip()
    a = obj.get("a")
    if isinstance(a, list) and a:
        # devuelve la primera
        return str(a[0])
    # fallback: resolver host desde la URL
    url = obj.get("url") or ""
    host = urlparse(url).hostname
    return resolve_ip(host)

def main():
    if len(sys.argv)!=2:
        print(f"Uso: python3 {sys.argv[0]} dominio.com"); sys.exit(1)
    domain = sys.argv[1].strip().lower()
    check_deps()

    print(BOLD(CYN(f"\n▌ Live subdomain probe ({domain}) — subfinder → httpx\n")))
    print(BOLD(f"{'STATUS':<8} │ {'URL':<60} │ {'TITLE':<45} │ IP"))

    # subfinder produce subdominios
    sf = subprocess.Popen(
        ["subfinder","-silent","-d",domain],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1
    )

    # httpx consume subdominios y emite JSON por línea
    hx = subprocess.Popen(
        HTTPX_ARGS,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1
    )

    # pasar subfinder -> httpx (streaming)
    def feeder():
        try:
            for line in sf.stdout:
                if stop_flag: break
                sub = line.strip()
                if not sub: continue
                try:
                    hx.stdin.write(sub+"\n")
                    hx.stdin.flush()
                except BrokenPipeError:
                    break
        finally:
            try:
                if hx.stdin: hx.stdin.close()
            except Exception:
                pass

    t = threading.Thread(target=feeder, daemon=True)
    t.start()

    # leer httpx stdout y mostrar solo exitosos (httpx ya filtra caídos)
    try:
        for line in hx.stdout:
            if stop_flag: break
            line=line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            status = obj.get("status_code","-")
            url    = obj.get("url","-")
            title  = obj.get("title","-")

            ip     = extract_ip(obj)

            # color por rango de status
            s = int(status) if isinstance(status,int) or (isinstance(status,str) and status.isdigit()) else 0
            if   200 <= s < 300: scol = GRN
            elif 300 <= s < 400: scol = CYN
            elif 400 <= s < 600: scol = RED
            else: scol = BLU

            print(f"{scol(f'[{status}]'):<8} │ {truncate(url,60):<60} │ {truncate(title,45):<45} │ {ip}", flush=True)
    finally:
        # cerrar procesos limpiamente
        try:
            if sf.poll() is None:
                sf.terminate()
                sf.wait(timeout=2)
        except Exception: pass
        try:
            if hx.poll() is None:
                hx.terminate()
                hx.wait(timeout=2)
        except Exception: pass

if __name__=="__main__":
    main()
