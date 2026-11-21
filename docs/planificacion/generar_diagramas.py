"""Genera los tableros Kanban por sprint y los diagramas de arquitectura y DevSecOps (HTML -> PNG)."""
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

import simulacion as sim

AQUI = Path(__file__).parent
HTML_DIR = AQUI.parent / 'html'
IMG = AQUI.parent / 'img'
HTML_DIR.mkdir(exist_ok=True)
IMG.mkdir(exist_ok=True)

COLOR_EPICA = {'E1': '#2f6b3f', 'E2': '#d98a1f', 'E3': '#3d6fa8', 'E4': '#8c4f9e', 'E5': '#b23a2b', 'E6': '#5c6b63'}
COLOR_ESTADO = {'To Do': '#e3e7e4', 'In Progress': '#3d6fa8', 'In Review': '#d98a1f', 'Done': '#2f6b3f'}

BASE_CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 28px; font-family: 'Segoe UI', system-ui, sans-serif; color: #1f2a24; background: #f6f4ef; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: #5d6b63; margin: 0 0 18px; font-size: 14px; }
"""


def tarjeta(hid, sprint):
    h = sim.HIST[hid]
    arr = ' · <b>arrastre</b>' if (sprint == 3 and hid == 'HU19') or (sprint == 4 and hid == 'HU19') else ''
    return (f"<div class='card' style='border-left-color:{COLOR_EPICA[h['epica']]}'>"
            f"<div class='top'><b>MS-{hid}</b><span class='sp'>{h['sp']} SP</span></div>"
            f"<div class='t'>{escape(h['titulo'])}</div>"
            f"<div class='meta'>{h['epica']} · {h['moscow']}{arr}</div></div>")


def html_kanban(sprint):
    s = sim.SPRINTS[sprint]
    dias = sim.dias_habiles(sprint)
    snaps = [3, 6, 10]
    tableros = []
    for d in snaps:
        t = sim.tablero(sprint, d)
        cols = []
        for col in ['To Do', 'In Progress', 'In Review', 'Done']:
            lim = sim.WIP.get(col)
            cuenta = f"{len(t[col])}/{lim}" if lim else str(len(t[col]))
            wip = f"<span class='wip'>WIP máx. {lim}</span>" if lim else ''
            cards = ''.join(tarjeta(h, sprint) for h in t[col]) or "<div class='vacio'>—</div>"
            cols.append(f"<div class='col'><div class='ch' style='border-top-color:{COLOR_ESTADO[col]}'>"
                        f"<span>{col}</span><span class='n'>{cuenta}</span></div>{wip}{cards}</div>")
        tableros.append(f"<div class='board'><div class='bt'>Día {d} · {dias[d-1].strftime('%d/%m/%Y')}</div>"
                        f"<div class='cols'>{''.join(cols)}</div></div>")

    filas = []
    for hid in sim.FLUJO[sprint]:
        celdas = ''.join(
            f"<td style='background:{COLOR_ESTADO[sim.estado(sprint, hid, d)]}' title='{sim.estado(sprint, hid, d)}'></td>"
            for d in range(1, sim.DIAS_SPRINT + 1))
        filas.append(f"<tr><th>MS-{hid} <small>{escape(sim.HIST[hid]['titulo'])}</small></th>{celdas}</tr>")
    cab = ''.join(f"<th class='d'>{d.strftime('%d/%m')}</th>" for d in dias)
    leyenda = ''.join(f"<span><i style='background:{c}'></i>{e}</span>" for e, c in COLOR_ESTADO.items())
    comp, hecho = sim.velocidad(sprint)
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{BASE_CSS}
.board {{ background:#fff; border:1px solid #dfe3dc; border-radius:12px; padding:12px; margin-bottom:14px; }}
.bt {{ font-weight:700; margin-bottom:8px; }}
.cols {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
.col {{ background:#f3f5f2; border-radius:10px; padding:8px; min-height:80px; }}
.ch {{ display:flex; justify-content:space-between; font-weight:700; font-size:13px; border-top:4px solid; padding-top:6px; }}
.n {{ color:#5d6b63; }}
.wip {{ display:block; font-size:11px; color:#b23a2b; margin:2px 0 4px; }}
.card {{ background:#fff; border:1px solid #dfe3dc; border-left:5px solid; border-radius:8px; padding:6px 8px; margin-top:6px; font-size:12px; }}
.card .top {{ display:flex; justify-content:space-between; }}
.sp {{ background:#eef1ee; border-radius:99px; padding:0 7px; }}
.card .t {{ margin:2px 0; }}
.meta {{ color:#5d6b63; font-size:11px; }}
.vacio {{ color:#9aa5a0; text-align:center; padding:10px; }}
table {{ border-collapse:separate; border-spacing:3px; background:#fff; border:1px solid #dfe3dc; border-radius:12px; padding:8px; width:100%; }}
table th {{ text-align:left; font-size:12px; white-space:nowrap; padding-right:8px; }}
table th small {{ color:#5d6b63; font-weight:400; }}
th.d {{ text-align:center; font-weight:600; color:#5d6b63; }}
td {{ height:20px; border-radius:4px; min-width:44px; }}
.ley {{ display:flex; gap:16px; font-size:12px; margin:8px 0 0; color:#5d6b63; }}
.ley i {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:5px; vertical-align:-2px; }}
h2 {{ font-size:16px; margin:18px 0 8px; }}
</style></head><body>
<h1>Tablero Kanban · Sprint {sprint}</h1>
<p class='sub'>{s['inicio']} a {s['fin']} · Objetivo: {escape(s['objetivo'])} · Velocidad {hecho}/{comp} SP · Límites WIP: In Progress 3, In Review 2</p>
{''.join(tableros)}
<h2>Flujo diario de cada historia</h2>
<table><tr><th>Historia</th>{cab}</tr>{''.join(filas)}</table>
<div class='ley'>{leyenda}</div>
</body></html>"""


ARQ = """<!doctype html><html lang='es'><head><meta charset='utf-8'><style>""" + BASE_CSS + """
.wrap { display:grid; grid-template-columns: 1fr 250px; gap:18px; }
.capa { background:#fff; border:1px solid #dfe3dc; border-radius:14px; padding:12px 14px; position:relative; }
.capa h3 { margin:0 0 8px; font-size:14px; text-transform:uppercase; letter-spacing:.04em; color:#5d6b63; }
.fila { display:flex; gap:10px; flex-wrap:wrap; }
.box { border:1.5px solid #2f6b3f; background:#f1f6f2; border-radius:10px; padding:8px 10px; font-size:13px; flex:1; min-width:120px; }
.box b { display:block; }
.box small { color:#5d6b63; }
.sec { border-color:#b23a2b; background:#fbf1ef; }
.ext { border-color:#3d6fa8; background:#eef3f9; }
.db { border-color:#8c4f9e; background:#f6f0f8; }
.flecha { text-align:center; color:#5d6b63; font-size:13px; margin:6px 0; }
.flecha b { font-size:18px; color:#1f2a24; }
.lado .capa { margin-bottom:12px; }
</style></head><body>
<h1>Arquitectura lógica · Mayorista Seguro</h1>
<p class='sub'>Aplicación web en capas desplegada como función serverless en Vercel, con PostgreSQL gestionado y seguridad transversal.</p>
<div class='wrap'><div>
 <div class='capa'><h3>Usuarios</h3><div class='fila'>
  <div class='box'><b>Administrador del mercado</b><small>Municipalidad: padrón, puestos, estiba, puertas, denuncias</small></div>
  <div class='box'><b>Inspector sanitario</b><small>Inspecciones por puesto</small></div>
  <div class='box'><b>Comerciante</b><small>Reservas de descarga, servicios de estiba</small></div>
  <div class='box'><b>Público / denunciante</b><small>Tarifas oficiales y denuncia anónima, sin cuenta</small></div>
 </div></div>
 <div class='flecha'><b>↓</b> HTTPS (TLS) · navegador</div>
 <div class='capa'><h3>Frontend · presentación</h3><div class='fila'>
  <div class='box'><b>SPA HTML + CSS + JavaScript</b><small>Servida como estáticos por la CDN de Vercel. Vista pública y panel por rol.</small></div>
  <div class='box sec'><b>Controles en el cliente</b><small>CSP estricta (solo 'self'), sin innerHTML (anti-XSS), token en sessionStorage</small></div>
 </div></div>
 <div class='flecha'><b>↓</b> REST/JSON sobre HTTPS · <code>Authorization: Bearer &lt;JWT&gt;</code></div>
 <div class='capa'><h3>Backend · API (Vercel Function, Node.js 22 + Express 5)</h3>
  <div class='fila' style='margin-bottom:8px'>
   <div class='box sec'><b>helmet</b><small>CSP, HSTS, nosniff, frame-ancestors</small></div>
   <div class='box sec'><b>Rate limiting</b><small>login 10/15 min, denuncias 20/h</small></div>
   <div class='box sec'><b>Autenticación</b><small>JWT HS256 8 h + bcrypt</small></div>
   <div class='box sec'><b>Autorización</b><small>roles admin / inspector / comerciante</small></div>
   <div class='box sec'><b>Validación zod</b><small>RUC, DNI, placa, fechas, enums</small></div>
  </div>
  <div class='fila'>
   <div class='box'><b>Auth</b><small>/auth/login, /auth/yo</small></div>
   <div class='box'><b>Padrón y puestos</b><small>/comerciantes, /puestos</small></div>
   <div class='box'><b>Estiba formal</b><small>/estibadores, /tarifas, /servicios-estiba</small></div>
   <div class='box'><b>Reservas</b><small>/reservas, /reservas/:id/ingreso</small></div>
   <div class='box'><b>Inspecciones</b><small>/inspecciones</small></div>
   <div class='box'><b>Denuncias</b><small>/denuncias, /seguimiento/:codigo</small></div>
   <div class='box'><b>Indicadores y auditoría</b><small>/indicadores, /auditoria, /salud</small></div>
  </div></div>
 <div class='flecha'><b>↓</b> SQL parametrizado ($1, $2…) · driver <code>pg</code> · TLS</div>
 <div class='capa'><h3>Datos</h3><div class='fila'>
  <div class='box db'><b>PostgreSQL (Neon, serverless)</b><small>usuarios, comerciantes, puestos, estibadores, tarifas_estiba, servicios_estiba, reservas_descarga, inspecciones, denuncias, auditoria</small></div>
  <div class='box db'><b>pg-mem</b><small>PostgreSQL en memoria para pruebas y desarrollo (mismo SQL)</small></div>
 </div></div>
</div>
<div class='lado'>
 <div class='capa'><h3>Servicios externos</h3>
  <div class='box ext' style='margin-bottom:8px'><b>GitHub</b><small>Repositorio, Pull Requests, Security (CodeQL, Dependabot)</small></div>
  <div class='box ext' style='margin-bottom:8px'><b>GitHub Actions</b><small>CI/CD: build, test, seguridad, deploy</small></div>
  <div class='box ext' style='margin-bottom:8px'><b>Vercel</b><small>Hosting, CDN, funciones serverless, logs, variables de entorno cifradas</small></div>
  <div class='box ext' style='margin-bottom:8px'><b>Neon</b><small>PostgreSQL gestionado con TLS</small></div>
  <div class='box ext'><b>Jira</b><small>Backlog, sprints y tablero</small></div>
 </div>
 <div class='capa'><h3>Leyenda</h3>
  <div class='box' style='margin-bottom:6px'><b>Componente funcional</b></div>
  <div class='box sec' style='margin-bottom:6px'><b>Control de seguridad</b></div>
  <div class='box db' style='margin-bottom:6px'><b>Almacenamiento</b></div>
  <div class='box ext'><b>Servicio externo</b></div>
 </div>
</div></div></body></html>"""

FASES = [
    ('Plan', 'Jira Software (Scrum)', 'Backlog con 6 épicas y 24 historias, sprints, tablero Kanban', 'Historias de seguridad (HU04, HU05, HU06, HU09) y casos de abuso del caso (cupos, extorsión) como criterios de aceptación'),
    ('Code', 'Git + GitHub, VS Code, ESLint', 'Ramas main / test / feature, commits convencionales, Pull Requests', 'Validación zod, SQL parametrizado, sin innerHTML, ESLint no-eval; revisión obligatoria vía PR'),
    ('Build', 'GitHub Actions + npm ci', 'Instalación reproducible con lockfile, lint y verificación de build', 'npm audit (SCA) y Dependabot sobre dependencias y actions'),
    ('Test', 'node:test + supertest', '31 pruebas de integración con cobertura y reporte JUnit', 'Pruebas de seguridad: token manipulado, 403 por rol, inyección SQL, enumeración de usuarios'),
    ('Release', 'Pull Request test → main', 'Solo se fusiona con el pipeline en verde', 'SAST con CodeQL y Semgrep, Gitleaks (secretos), dependency review'),
    ('Deploy', 'Vercel CLI desde Actions', 'main → producción, test → preview, prueba de humo', 'Token en GitHub Secrets, JWT_SECRET y DATABASE_URL como variables cifradas, HTTPS + HSTS'),
    ('Operate', 'Vercel Functions + Neon PostgreSQL', 'Serverless con escalado automático', 'helmet/CSP, rate limiting, roles de mínimo privilegio, TLS hacia la base'),
    ('Monitor', 'Vercel logs, /api/salud, auditoría', 'Indicadores de negocio y salud del servicio', 'Tabla de auditoría, CodeQL semanal programado, alertas de Dependabot'),
]


def html_devsecops():
    filas = ''.join(
        f"<div class='fase'><div class='n'>{i}</div><div class='nom'>{f}</div>"
        f"<div class='c herr'><b>{escape(h)}</b></div><div class='c'>{escape(u)}</div><div class='c seg'>{escape(s)}</div></div>"
        for i, (f, h, u, s) in enumerate(FASES, start=1))
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{BASE_CSS}
.cab, .fase {{ display:grid; grid-template-columns: 40px 110px 1fr 1.3fr 1.6fr; gap:10px; align-items:stretch; }}
.cab div {{ font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:#5d6b63; font-weight:700; padding:0 8px; }}
.fase {{ margin-top:8px; }}
.n {{ display:grid; place-items:center; background:#2f6b3f; color:#fff; border-radius:10px; font-weight:700; }}
.nom {{ display:flex; align-items:center; font-weight:700; font-size:16px; }}
.c {{ background:#fff; border:1px solid #dfe3dc; border-radius:10px; padding:8px 10px; font-size:13px; }}
.herr {{ border-left:5px solid #3d6fa8; }}
.seg {{ border-left:5px solid #b23a2b; background:#fbf6f4; }}
.loop {{ margin-top:14px; font-size:13px; color:#5d6b63; }}
</style></head><body>
<h1>Ciclo de vida DevSecOps · herramientas y seguridad por fase</h1>
<p class='sub'>La seguridad se mueve a la izquierda (shift-left): cada fase tiene un control automático que bloquea el avance si falla.</p>
<div class='cab'><div>#</div><div>Fase</div><div>Herramienta</div><div>Uso en el proyecto</div><div>Control de seguridad integrado</div></div>
{filas}
<p class='loop'>Monitor retroalimenta Plan: hallazgos de CodeQL/Dependabot, denuncias y auditoría generan nuevas historias en el backlog de Jira.</p>
</body></html>"""


def render(nombre, html, ancho=1400):
    ruta = HTML_DIR / f'{nombre}.html'
    ruta.write_text(html, encoding='utf-8')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': ancho, 'height': 800}, device_scale_factor=2)
        pg.goto(ruta.as_uri())
        pg.screenshot(path=str(IMG / f'{nombre}.png'), full_page=True)
        b.close()


if __name__ == '__main__':
    sim.verificar_wip()
    for sp in sim.FLUJO:
        render(f'kanban_sprint{sp}', html_kanban(sp))
    render('arquitectura', ARQ, 1500)
    render('devsecops', html_devsecops(), 1500)
    print('Diagramas en', IMG)
