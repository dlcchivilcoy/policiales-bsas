# -*- coding: utf-8 -*-
"""El informe de cada pasada en HTML (se abre con doble clic): qué se capturó, qué se agrupó como
duplicado, el puntaje desglosado, qué se eligió y por qué, y cada pieza como saldría en cada red.
Las imágenes y los videos van al lado del HTML (rutas relativas)."""
import html
import os
from pathlib import Path

from agro import scoring as SC

ROTULOS = {"impacto_economico": "Impacto económico", "interes_productores": "Interés productores",
           "innovacion": "Innovación", "cercania_argentina": "Cercanía Argentina", "cercania_pba": "Cercanía PBA",
           "potencial_reel": "Potencial reel", "conversacion": "Conversación", "potencial_comercial": "Comercial"}

CSS = """
:root{--bg:#f5f6f8;--card:#fff;--tx:#16181d;--sub:#5b616b;--borde:#e3e6ea;--nar:#ff7000;--ver:#5e9e2c;--alerta:#b54708;--fondo-alerta:#fff4e5}
@media (prefers-color-scheme:dark){:root{--bg:#111317;--card:#1a1d23;--tx:#eceef1;--sub:#a3a9b3;--borde:#2b2f37;--alerta:#f5a524;--fondo-alerta:#2a2112}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 80px}h1{font-size:26px;margin:0 0 4px}h2{margin:36px 0 12px;font-size:20px}
.sub{color:var(--sub)}.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.kpi{background:var(--card);border:1px solid var(--borde);border-radius:10px;padding:10px 14px;min-width:120px}
.kpi b{display:block;font-size:22px}.card{background:var(--card);border:1px solid var(--borde);border-radius:14px;padding:18px;margin:16px 0}
.pieza{display:grid;grid-template-columns:300px 1fr;gap:20px}@media(max-width:820px){.pieza{grid-template-columns:1fr}}
.pieza img,.pieza video{width:100%;border-radius:10px;border:1px solid var(--borde);display:block;margin-bottom:10px}
.tag{display:inline-block;border-radius:99px;padding:2px 10px;font-size:12px;font-weight:600;margin-right:6px;background:var(--borde)}
.tag.nar{background:var(--nar);color:#fff}.tag.ver{background:var(--ver);color:#fff}.tag.alerta{background:var(--alerta);color:#fff}
table{border-collapse:collapse;width:100%}td,th{padding:6px 8px;border-bottom:1px solid var(--borde);text-align:left;vertical-align:top;font-size:14px}
th{color:var(--sub);font-weight:600}.num{text-align:right;white-space:nowrap}.barra{height:6px;background:var(--borde);border-radius:3px;min-width:60px}
.barra i{display:block;height:6px;background:var(--ver);border-radius:3px}pre{white-space:pre-wrap;font:14px/1.5 system-ui,sans-serif;margin:0}
details{border:1px solid var(--borde);border-radius:10px;padding:8px 12px;margin:8px 0}summary{cursor:pointer;font-weight:600}
.alerta{background:var(--fondo-alerta);border-left:4px solid var(--alerta);padding:10px 12px;border-radius:6px;margin:10px 0}
a{color:var(--nar)}.tabla-scroll{overflow-x:auto}
"""


def e(t) -> str:
    return html.escape(str(t if t is not None else ""))


def _rel(ruta, carpeta: Path) -> str:
    if not ruta:
        return ""
    try:
        return Path(os.path.relpath(ruta, carpeta)).as_posix()
    except ValueError:
        return Path(ruta).as_uri()


def _tabla_score(s: dict) -> str:
    filas = "".join(
        f"<tr><td>{ROTULOS[c]}</td><td class=num>{s.get(c, 0)} / {tope}</td>"
        f"<td><div class=barra><i style='width:{100 * s.get(c, 0) / tope:.0f}%'></i></div></td></tr>"
        for c, tope in SC.CRITERIOS.items())
    doble = (f"<tr><td>Doble puntaje (cerca del corte)</td><td class=num>{s['dobles'][0]} y {s['dobles'][1]}"
             f" → promedio</td><td></td></tr>") if s.get("dobles") else ""
    return (f"<table>{filas}<tr><th>Total</th><th class=num>{s.get('ai_score')} / 100</th><th></th></tr>{doble}"
            f"<tr><td>Comercial (sponsors)</td><td class=num>{s.get('commercial_score')} / 100</td><td></td></tr></table>")


def _pieza(p: dict, carpeta: Path) -> str:
    g, s = p["guion"], p["score"]
    tags = [f"<span class='tag ver'>{e(s['subtema'])}</span>", f"<span class=tag>{e(s.get('tema'))}</span>",
            f"<span class=tag>{e(s['ambito'])}</span>"]
    if g.get("requires_review"):
        tags.append("<span class='tag alerta'>REQUIERE REVISIÓN</span>")
    if not g.get("apta"):
        tags.append("<span class='tag alerta'>NO APTA</span>")
    medios = ""
    if p.get("portada"):
        medios += f"<img src='{e(_rel(p['portada'], carpeta))}' alt='portada'>"
    if (p.get("reel") or {}).get("archivo"):
        medios += f"<video controls preload=metadata src='{e(_rel(p['reel']['archivo'], carpeta))}'></video>"
    img = p.get("imagen") or {}
    alerta = ""
    if g.get("requires_review"):
        alerta = f"<div class=alerta><b>No se publicaría sola:</b> {e(g.get('motivo_revision'))}</div>"
    elif not g.get("apta"):
        alerta = f"<div class=alerta><b>No apta:</b> {e(g.get('motivo'))}</div>"
    fuentes = "".join(f"<li><a href='{e(n['url'])}' target=_blank>{e(n['fuente'])}: {e(n['titulo'])}</a>"
                      f" <span class=sub>({e(n.get('tipo_fuente'))})</span></li>" for n in p["grupo"])
    plan = "".join(f"<tr><td>{e(r)}</td><td>{e(v)}</td></tr>" for r, v in (p.get("plan") or {}).items())
    textos = "".join(f"<details><summary>{e(t)}</summary><pre>{e(v)}</pre></details>"
                     for t, v in (p.get("textos") or {}).items())
    reel = g.get("reel") or {}
    guion_reel = (f"<details><summary>Guion del reel</summary><table>"
                  f"<tr><td>0-3 s gancho</td><td>{e(reel.get('gancho'))}</td></tr>"
                  f"<tr><td>3-7 s qué pasó</td><td>{e(reel.get('que_paso'))}</td></tr>"
                  f"<tr><td>7-12 s datos</td><td>{'<br>'.join(e(d) for d in reel.get('datos') or [])}</td></tr>"
                  f"<tr><td>12-16 s por qué importa</td><td>{e(reel.get('por_que_importa'))}</td></tr>"
                  f"<tr><td>16-19 s cierre</td><td>{e(reel.get('cierre'))}</td></tr></table></details>")
    controles = (f"<details><summary>Controles</summary><table>"
                 f"<tr><td>Copia más larga del original</td><td>{e((g.get('copia') or {}).get('racha'))} palabras"
                 f" {('— «' + e((g.get('copia') or {}).get('tramo')) + '»') if (g.get('copia') or {}).get('tramo') else ''}</td></tr>"
                 f"<tr><td>Párrafos corregidos por copia</td><td>{e(g.get('reparaciones_copia') or 0)}</td></tr>"
                 f"<tr><td>Datos que faltan en el texto</td><td>{e(', '.join(g.get('faltan_datos') or []) or 'ninguno')}</td></tr>"
                 f"<tr><td>Formato</td><td>{e('; '.join(g.get('formato') or []) or 'ok')}</td></tr>"
                 f"<tr><td>Imagen</td><td>{e(img.get('origen'))} — {e(img.get('motivo'))}"
                 f"{(' · <a href=' + chr(39) + e(img.get('url_original')) + chr(39) + ' target=_blank>foto original</a>') if img.get('url_original') else ''}</td></tr>"
                 f"<tr><td>IA</td><td>{e(g.get('via'))}</td></tr></table></details>")
    return (f"<div class='card pieza'><div>{medios}</div><div>{''.join(tags)}"
            f"<h3 style='margin:10px 0 4px'>{e(g.get('titular'))}</h3><p class=sub style='margin:0 0 10px'>{e(g.get('bajada'))}</p>"
            f"{alerta}<p><b>Por qué:</b> {e(s.get('explicacion'))}</p>{_tabla_score(s)}"
            f"<h4>Plan de publicación (simulado)</h4><table>{plan}</table>"
            f"<h4>Textos por red</h4>{textos}{guion_reel}{controles}"
            f"<h4>Fuentes del grupo (solo para trazabilidad, no se publican)</h4><ul>{fuentes}</ul></div></div>")


def escribir(inf: dict, carpeta: Path) -> Path:
    carpeta = Path(carpeta)
    c = inf["conteos"]
    kpis = "".join(f"<div class=kpi><b>{e(v)}</b>{e(k)}</div>" for k, v in c.items())
    fuentes = "".join(f"<tr><td>{e(f['fuente'])}</td><td class=num>{f['leidas']}</td><td class=num>{f['nuevas']}</td>"
                      f"<td>{e('; '.join(f['errores']) or 'ok')}</td></tr>" for f in inf["fuentes"])
    piezas = "".join(_pieza(p, carpeta) for p in inf["piezas"]) or "<p class=sub>No salió ninguna pieza en esta pasada.</p>"
    grupos = "".join(
        f"<details><summary>{len(g['notas'])} notas · {e(g['notas'][0]['titulo'])}</summary><ul>"
        + "".join(f"<li>{e(n['fuente'])}: <a href='{e(n['url'])}' target=_blank>{e(n['titulo'])}</a>"
                  f" <span class=sub>({e(g['como'].get(n['id'], ''))})</span></li>" for n in g["notas"])
        + "</ul></details>" for g in inf["grupos_duplicados"]) or "<p class=sub>Ninguno.</p>"
    desc = "".join(
        f"<tr><td>{e(d['fuente'])}</td><td><a href='{e(d['url'])}' target=_blank>{e(d['titulo'])}</a></td>"
        f"<td class=num>{e(d.get('score', ''))}{('<br><span class=sub>' + e(d['dobles'][0]) + ' y ' + e(d['dobles'][1]) + '</span>') if d.get('dobles') else ''}</td><td>{e(d.get('subtema', ''))}</td><td>{e(d['motivo'])}"
        f"{('<br><span class=sub>' + e(d['explicacion']) + '</span>') if d.get('explicacion') else ''}</td></tr>"
        for d in inf["descartadas"])
    cuerpo = (f"<main><h1>Agro · pasada {'real' if inf.get('publicar') else 'simulada'}</h1><div class=sub>{e(inf['cuando'])} · @diarioyradioagro · "
              f"<b>{'PUBLICADA' if inf.get('publicar') else 'no se publicó nada'}</b> · score mínimo {inf['config']['score_min']} · tope {inf['config']['max_dia']} por día</div>"
              f"<div class=kpis>{kpis}</div>"
              f"<h2>Piezas</h2>{piezas}"
              f"<h2>Fuentes</h2><div class=tabla-scroll><table><tr><th>Fuente</th><th class=num>Leídas</th>"
              f"<th class=num>Últimas {inf['config']['horas']} h</th><th>Estado</th></tr>{fuentes}</table></div>"
              f"<h2>Duplicados agrupados</h2>{grupos}"
              f"<h2>Descartadas y por qué</h2><div class=tabla-scroll><table><tr><th>Fuente</th><th>Nota</th>"
              f"<th class=num>Score</th><th>Subtema</th><th>Motivo</th></tr>{desc}</table></div></main>")
    ruta = carpeta / "informe.html"
    ruta.write_text(f"<!doctype html><html lang=es><head><meta charset=utf-8>"
                    f"<meta name=viewport content='width=device-width,initial-scale=1'><title>Agro simulación</title>"
                    f"<style>{CSS}</style></head><body>{cuerpo}</body></html>", encoding="utf-8")
    return ruta
