# -*- coding: utf-8 -*-
"""Cosecha el directorio de plusnoticias para las 28 localidades: devuelve candidatos
(nombre + dominio) por ciudad. Es solo una SEMILLA: el directorio esta desactualizado,
asi que despues se completa a mano y se mide el flujo real con sondear_medios.py."""
import httpx, json, re, unicodedata
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.plusnoticias.com.ar/ciudades.asp?id_ciudad="

LOCALIDADES = ["Suipacha","Mercedes","Lujan","25 de Mayo","Saladillo","Alberti","Bragado",
"Chacabuco","Junin","Lincoln","9 de Julio","Carlos Casares","Trenque Lauquen","Bolivar",
"Pehuajo","Carmen de Areco","San Andres de Giles","San Antonio de Areco","Salto","Arrecifes",
"Pergamino","Rojas","Lobos","Canuelas","San Miguel del Monte","Las Flores","Navarro","Roque Perez"]

def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()

def soup_of(url):
    r = httpx.get(url, headers=H, timeout=30, follow_redirects=True)
    return BeautifulSoup(r.content.decode("latin-1", errors="replace"), "html.parser")

# 1) mapa ciudad -> id desde la barra lateral
s = soup_of(BASE + "286")
ids = {}
for a in s.find_all("a", href=re.compile(r"ciudades\.asp\?id_ciudad=")):
    ids.setdefault(norm(a.get_text(" ", strip=True)), re.search(r"=(\d+)", a["href"]).group(1))
print(f"ciudades en el directorio: {len(ids)}")

out = {}
for loc in LOCALIDADES:
    key = norm(loc)
    cid = ids.get(key) or ids.get(key.replace("san miguel del monte", "monte"))
    if not cid:
        # busqueda laxa por substring
        cand = [v for k, v in ids.items() if key in k or k in key]
        cid = cand[0] if cand else None
    if not cid:
        print(f"  [!] {loc}: sin entrada en el directorio")
        out[loc] = []
        continue
    try:
        cs = soup_of(BASE + cid)
    except Exception as e:
        print(f"  [!] {loc}: {e}")
        out[loc] = []
        continue
    medios, vistos = [], set()
    for a in cs.find_all("a", href=True):
        h = a["href"].strip()
        if not h.startswith("http") or "plusnoticias" in h or "addthis" in h:
            continue
        nombre = a.get_text(" ", strip=True)
        if not nombre or nombre.lower().startswith(("diario digital", "actualidad", "actualizate", "diario de noticias")):
            continue
        dom = re.sub(r"^https?://(www\.)?", "", h).split("/")[0].lower()
        if dom in vistos:
            continue
        vistos.add(dom)
        medios.append({"nombre": nombre, "url": h.strip()})
    out[loc] = medios
    print(f"  {loc} (id {cid}): {len(medios)} candidatos")

with open("data/candidatos_directorio.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n-> data/candidatos_directorio.json")
