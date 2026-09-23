# -*- coding: utf-8 -*-
"""Arma una pagina local para revisar los reels de una corrida antes de publicar.

Por que existe: los reels quedan como un monton de .jpg, .mp4 y .json sueltos en
una carpeta. Para decidir si una tanda sale o no sale hay que ver la placa, el
video y el texto del posteo JUNTOS, y uno al lado del otro — no abriendo catorce
archivos a mano.

Es una pagina LOCAL: vive adentro de la carpeta de la corrida y apunta a los
archivos por ruta relativa. No sube nada a ningun lado ni necesita internet.

Correr:  venv\\Scripts\\python.exe tools\\galeria.py            (la ultima corrida)
         venv\\Scripts\\python.exe tools\\galeria.py <carpeta>
"""
import base64
import glob
import html
import io
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# La placa es de 1080x1920 y pesa ~400 KB. Catorce de esas embebidas en la pagina
# son 7 MB y la vuelven pesada al pedo: para revisar alcanza con una miniatura, y el
# archivo grande esta a un clic. 380 px de ancho es lo que entra comodo en la tarjeta
# en una pantalla normal, contando que el navegador la muestra al doble en retina.
ANCHO_MINIATURA = 380


def _miniatura(ruta):
    """La placa como data: URI, achicada. Devuelve "" si no se puede.

    Va embebida y no por ruta relativa a proposito: asi la pagina se ve igual esté
    donde esté —abierta desde otra carpeta, mandada por mail, mirada en un panel—
    y no queda dependiendo de que los .jpg sigan al lado. Los archivos grandes se
    borran a los pocos dias; esta pagina sobrevive.
    """
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            im = im.convert("RGB")
            alto = round(im.height * ANCHO_MINIATURA / im.width)
            im = im.resize((ANCHO_MINIATURA, alto), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=78, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _ultima_corrida():
    carpetas = sorted(glob.glob(os.path.join(RAIZ, "salida_reels", "*")))
    carpetas = [c for c in carpetas if os.path.isdir(c)]
    return carpetas[-1] if carpetas else None


CSS = """
:root{--fondo:#12141a;--caja:#1b1e26;--borde:#2a2f3a;--texto:#e8eaed;--suave:#9aa3b2;
      --naranja:#f77f00;--ok:#2ea043;--mal:#d13438}
*{box-sizing:border-box}
body{margin:0;padding:24px;background:var(--fondo);color:var(--texto);
     font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--suave);margin-bottom:24px;font-size:14px}
.aviso{background:#2a2213;border:1px solid #6b5423;border-radius:8px;padding:12px 16px;
       margin-bottom:24px;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:20px}
.card{background:var(--caja);border:1px solid var(--borde);border-radius:12px;overflow:hidden;
      display:flex;flex-direction:column}
.cab{padding:12px 16px;border-bottom:1px solid var(--borde);display:flex;
     justify-content:space-between;align-items:center;gap:10px}
.loc{font-weight:600}
.badge{font-size:11px;padding:3px 9px;border-radius:99px;font-weight:600;white-space:nowrap}
.si{background:rgba(46,160,67,.18);color:#5ddb7e;border:1px solid rgba(46,160,67,.4)}
.no{background:rgba(209,52,56,.15);color:#ff8a8d;border:1px solid rgba(209,52,56,.4)}
.medios{display:flex;gap:12px;padding:16px;align-items:flex-start}
.medios img,.medios video{width:180px;border-radius:8px;background:#000;flex:0 0 auto}
.txt{padding:0 16px 16px;font-size:14px}
.campo{margin-bottom:10px}
.et{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--suave);
    margin-bottom:2px}
.volanta{color:var(--naranja);font-weight:600}
.titular{font-size:17px;font-weight:700;line-height:1.25}
.desc{background:#0f1116;border:1px solid var(--borde);border-radius:8px;padding:12px;
      white-space:pre-wrap;font-size:13px;color:#cfd4dc;max-height:220px;overflow:auto}
.pie-card{padding:10px 16px;border-top:1px solid var(--borde);display:flex;gap:14px;
          font-size:12px;color:var(--suave);flex-wrap:wrap;align-items:center}
.pie-card a{color:#7aa7ff}
button{background:#252a33;color:var(--texto);border:1px solid var(--borde);border-radius:6px;
       padding:5px 11px;font-size:12px;cursor:pointer;font-family:inherit}
button:hover{background:#2e3540}
.porque{color:#ff8a8d;font-size:12px;padding:0 16px 12px}
"""

JS = """
function copiar(id, btn){
  const t = document.getElementById(id).innerText;
  navigator.clipboard.writeText(t).then(()=>{
    const antes = btn.textContent; btn.textContent = 'copiado';
    setTimeout(()=>btn.textContent = antes, 1200);
  });
}
"""


def construir(carpeta):
    piezas = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "[0-9]*.json"))):
        with open(ruta, encoding="utf-8") as f:
            piezas.append((os.path.basename(ruta)[:-5], json.load(f)))
    if not piezas:
        return None

    aptos = sum(1 for _, p in piezas if p.get("apto_para_publicar"))
    # Los horarios salen del plan que arma reels/flujo.py: cinco minutos entre pieza
    # y pieza, para que la cuenta no parezca un script vaciando una cola.
    horas = sorted(p["publicar_en"] for _, p in piezas if p.get("publicar_en"))
    cadencia = (f"Cuando se conecte la publicación, la tanda sale escalonada: "
                f"de {horas[0][11:]} a {horas[-1][11:]}, una cada 5 minutos."
                if len(horas) > 1 else "")
    tarjetas = []
    for base, p in piezas:
        g = p.get("guion", {})
        e = html.escape
        apto = p.get("apto_para_publicar")
        jpg, mp4 = base + ".jpg", base + ".mp4"
        mini = _miniatura(os.path.join(carpeta, jpg))
        video = (f'<video src="{e(mp4)}" controls muted preload="metadata"></video>'
                 if os.path.exists(os.path.join(carpeta, mp4)) else "")
        desc_id = "d_" + base.replace("-", "_").replace(".", "_")

        tarjetas.append(f"""
  <div class="card">
    <div class="cab">
      <span class="loc">{e(str(p.get('localidad','')))}</span>
      <span class="badge {'si' if apto else 'no'}">
        {('SALE ' + p['publicar_en'][11:]) if (apto and p.get('publicar_en'))
         else ('LISTO PARA TIKTOK' if apto else 'NO PUBLICABLE')}</span>
    </div>
    <div class="medios">
      <a href="{e(jpg)}" target="_blank" title="abrir la placa en tamaño real">
        <img src="{mini or e(jpg)}" alt="placa"></a>{video}</div>
    {'' if apto else f'<div class="porque">{e(p.get("por_que_no",""))}</div>'}
    <div class="txt">
      <div class="campo"><div class="et">Volanta</div>
        <div class="volanta">{e(str(g.get('volanta','')))}</div></div>
      <div class="campo"><div class="et">Titular</div>
        <div class="titular">{e(str(g.get('titular','')))}</div></div>
      <div class="campo"><div class="et">Bajada</div>
        <div>{e(str(g.get('bajada','')))}</div></div>
      <div class="campo"><div class="et">Zócalo</div>
        <div>{e(str(g.get('zocalo','')))}</div></div>
      <div class="campo">
        <div class="et">Descripción del posteo
          <button onclick="copiar('{desc_id}',this)">copiar</button></div>
        <div class="desc" id="{desc_id}">{e(p.get('descripcion_tiktok',''))}</div>
      </div>
    </div>
    <div class="pie-card">
      <span>{e(str(p.get('tipo','')))}</span>
      <span>·</span>
      <span>{e(str(p.get('medio','')))}</span>
      <span>·</span>
      <a href="{e(str(p.get('url_original','')))}" target="_blank">nota original</a>
      <span>·</span>
      <span>{e(str(g.get('via','')))}</span>
    </div>
  </div>""")

    pagina = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Reels para revisar — {html.escape(os.path.basename(carpeta))}</title>
<style>{CSS}</style></head><body>
<h1>Reels de policiales — {html.escape(os.path.basename(carpeta))}</h1>
<div class="sub">{len(piezas)} piezas · {aptos} listas para publicar ·
  {len(piezas) - aptos} con objeciones</div>
<div class="aviso"><strong>No se publicó nada.</strong> Esta página es para mirar cómo
  quedarían los reels antes de que salgan. Vive en tu disco: no sube nada a ningún lado.
  {cadencia}</div>
<div class="grid">{''.join(tarjetas)}</div>
<script>{JS}</script></body></html>"""

    destino = os.path.join(carpeta, "galeria.html")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(pagina)
    return destino, len(piezas), aptos


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else _ultima_corrida()
    if not carpeta or not os.path.isdir(carpeta):
        print("No encontre ninguna corrida en salida_reels/.")
        return 1
    r = construir(carpeta)
    if not r:
        print(f"La carpeta {carpeta} no tiene piezas.")
        return 1
    destino, total, aptos = r
    print(f"{total} piezas ({aptos} publicables) -> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
