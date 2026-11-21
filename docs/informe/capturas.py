"""Capturas automáticas para el informe: la app en producción y las páginas públicas de GitHub."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = 'https://mayorista-seguro.vercel.app'
REPO = 'https://github.com/MaylorVR/laparada-mayorista-seguro'
OUT = Path(__file__).parent.parent / 'evidencias'
OUT.mkdir(exist_ok=True)


def app(b):
    pg = b.new_page(viewport={'width': 1366, 'height': 850}, color_scheme='light')
    pg.goto(APP, wait_until='networkidle')
    pg.screenshot(path=str(OUT / 'app_publica.png'), full_page=True)
    pg.fill('#form-login input[name=email]', 'admin@mayorista.pe')
    pg.fill('#form-login input[name=password]', 'Demo2026!')
    pg.click('#form-login button')
    pg.wait_for_selector('.kpis')
    pg.screenshot(path=str(OUT / 'app_indicadores.png'))
    for tab, nombre in [('Estiba', 'app_estiba'), ('Reservas', 'app_reservas'), ('Denuncias', 'app_denuncias')]:
        pg.click(f'#tabs button[data-v={tab}]')
        pg.wait_for_timeout(1200)
        pg.screenshot(path=str(OUT / f'{nombre}.png'), full_page=True)


def github(b, rutas):
    pg = b.new_page(viewport={'width': 1366, 'height': 900}, color_scheme='light')
    for nombre, ruta in rutas:
        pg.goto(REPO + ruta, wait_until='networkidle')
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(OUT / f'{nombre}.png'), full_page=nombre.endswith('pruebas'))


if __name__ == '__main__':
    with sync_playwright() as p:
        b = p.chromium.launch()
        if 'app' in sys.argv:
            app(b)
        if 'github' in sys.argv:
            rutas = [a.split('=', 1) for a in sys.argv if '=' in a]
            github(b, rutas)
        b.close()
    print('ok')
