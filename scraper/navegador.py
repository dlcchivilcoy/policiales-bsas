# -*- coding: utf-8 -*-
"""Respaldo con navegador real para los sitios que httpx no puede leer.

Se usa en dos casos y solo en esos, porque es entre 10 y 20 veces mas lento que
un GET comun:
  - el sitio responde 403 (proteccion tipo Cloudflare contra clientes automaticos)
  - la home viene vacia porque el listado se arma con JavaScript

Igual que en NoticIAs Chivilcoy, en Windows hay que usar channel="chrome" (el
Chrome instalado en el sistema): el Chromium que trae Playwright falla por SxS
en esta maquina.

Nada de esto elude un login ni un muro de pago: son paginas publicas que
cualquiera abre en su navegador. El respaldo solo hace que el scraper se
presente como lo que ya es, un navegador leyendo una nota publica.
"""
import sys
from bs4 import BeautifulSoup

_ESPERA_MS = 2500


def disponible() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _opciones_launch():
    opts = {"headless": True}
    if sys.platform == "win32":
        opts["channel"] = "chrome"
    return opts


def html_de(url, espera_ms=_ESPERA_MS, timeout_ms=30000):
    """Devuelve el HTML ya renderizado, o None si no se pudo."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[navegador] Playwright no instalado; se omite el respaldo.")
        return None
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(**_opciones_launch())
            pagina = navegador.new_page()
            try:
                pagina.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                pagina.wait_for_timeout(espera_ms)
                return pagina.content()
            finally:
                navegador.close()
    except Exception as e:
        print(f"[navegador] {url[:60]}: {type(e).__name__}")
        return None


def htmls_de(urls, espera_ms=_ESPERA_MS, timeout_ms=30000):
    """Varias URLs en UNA sola sesion de navegador.

    Abrir y cerrar Chrome por cada URL es lo caro; reusando la pestaña, bajar 10
    paginas cuesta casi lo mismo que bajar una. Devuelve {url: html_o_None}.
    """
    salida = {u: None for u in urls}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[navegador] Playwright no instalado; se omite el respaldo.")
        return salida
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(**_opciones_launch())
            pagina = navegador.new_page()
            try:
                for u in urls:
                    try:
                        pagina.goto(u, timeout=timeout_ms, wait_until="domcontentloaded")
                        pagina.wait_for_timeout(espera_ms)
                        salida[u] = pagina.content()
                    except Exception as e:
                        print(f"[navegador] {u[:60]}: {type(e).__name__}")
            finally:
                navegador.close()
    except Exception as e:
        print(f"[navegador] sesion fallida: {type(e).__name__}: {e}")
    return salida


def soup_de(url, **kw):
    html = html_de(url, **kw)
    return BeautifulSoup(html, "html.parser") if html else None
