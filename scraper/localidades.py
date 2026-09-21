# -*- coding: utf-8 -*-
"""Nombres de las 28 localidades, bien escritos.

El padrón interno (`data/candidatos.json`, `scraper/medios.py`) usa las claves SIN
tildes ni eñes, porque son claves y así no se rompen al comparar ni al armar nombres de
archivo. Pero lo que se PUBLICA tiene que estar bien escrito: una placa que dice
«ROBO EN CANUELAS» ya salió mal, y además queda para siempre en el video.

Misma idea que `utils/branding.py` en social_publisher: una sola fuente de verdad para
cómo se escribe cada nombre, en vez de repetirlo suelto por cada archivo.
"""

# clave interna (sin tildes) -> cómo se escribe de verdad
NOMBRES = {
    "suipacha": "Suipacha",
    "mercedes": "Mercedes",
    "lujan": "Luján",
    "25 de mayo": "25 de Mayo",
    "saladillo": "Saladillo",
    "alberti": "Alberti",
    "bragado": "Bragado",
    "chacabuco": "Chacabuco",
    "junin": "Junín",
    "lincoln": "Lincoln",
    "9 de julio": "9 de Julio",
    "carlos casares": "Carlos Casares",
    "trenque lauquen": "Trenque Lauquen",
    "bolivar": "Bolívar",
    "pehuajo": "Pehuajó",
    "carmen de areco": "Carmen de Areco",
    "san andres de giles": "San Andrés de Giles",
    "san antonio de areco": "San Antonio de Areco",
    "salto": "Salto",
    "arrecifes": "Arrecifes",
    "pergamino": "Pergamino",
    "rojas": "Rojas",
    "lobos": "Lobos",
    "canuelas": "Cañuelas",
    "san miguel del monte": "San Miguel del Monte",
    "las flores": "Las Flores",
    "navarro": "Navarro",
    "roque perez": "Roque Pérez",
}


def nombre(localidad: str) -> str:
    """Devuelve el nombre bien escrito. Si no está en la tabla, lo deja como vino:
    mejor el nombre crudo que perderlo."""
    if not localidad:
        return ""
    return NOMBRES.get(localidad.strip().lower(), localidad.strip())
