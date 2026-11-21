"""Genera el informe de la práctica (Word) con textos, tablas, gráficos y capturas."""
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[2]
IMG = RAIZ / 'docs' / 'img'
EV = RAIZ / 'docs' / 'evidencias'
BL = json.loads((RAIZ / 'docs' / 'planificacion' / 'backlog.json').read_text(encoding='utf-8'))

ENLACES = {
    'Repositorio GitHub': 'https://github.com/MaylorVR/laparada-mayorista-seguro',
    'Proyecto Jira': 'https://maylorvr.atlassian.net/jira/software/projects/MS/boards/68/backlog',
    'Solución desplegada (Vercel)': 'https://mayorista-seguro.vercel.app',
    'Pipeline (GitHub Actions)': 'https://github.com/MaylorVR/laparada-mayorista-seguro/actions',
}
EXTRA = json.loads((Path(__file__).parent / 'enlaces_extra.json').read_text(encoding='utf-8')) \
    if (Path(__file__).parent / 'enlaces_extra.json').exists() else {}
ENLACES.update(EXTRA)

VERDE = RGBColor(0x1F, 0x4E, 0x2F)

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2)
estilo = doc.styles['Normal']
estilo.font.name = 'Calibri'
estilo.font.size = Pt(10.5)
for nivel, tam in [(1, 16), (2, 13), (3, 11.5)]:
    h = doc.styles[f'Heading {nivel}']
    h.font.name = 'Calibri'
    h.font.size = Pt(tam)
    h.font.color.rgb = VERDE


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tcPr.append(shd)


def tabla(cabecera, filas, anchos=None, tam=9):
    t = doc.add_table(rows=1, cols=len(cabecera))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(cabecera):
        cel = t.rows[0].cells[i]
        cel.text = ''
        r = cel.paragraphs[0].add_run(c)
        r.bold = True
        r.font.size = Pt(tam)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(cel, '1F4E2F')
    for fila in filas:
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            celdas[i].text = ''
            r = celdas[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(tam)
    if anchos:
        for fila in t.rows:
            for i, w in enumerate(anchos):
                fila.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def p(texto, negrita=None):
    par = doc.add_paragraph()
    if negrita:
        par.add_run(negrita).bold = True
    par.add_run(texto)
    return par


def viñetas(items):
    for it in items:
        if isinstance(it, tuple):
            par = doc.add_paragraph(style='List Bullet')
            par.add_run(it[0]).bold = True
            par.add_run(it[1])
        else:
            doc.add_paragraph(it, style='List Bullet')


def imagen(ruta, pie, ancho=16.5):
    if not Path(ruta).exists():
        p(f'[Falta la imagen {Path(ruta).name}]')
        return
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph(pie)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.runs[0].italic = True
    cap.runs[0].font.size = Pt(9)


def enlace(par, texto, url):
    rid = par.part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    h = OxmlElement('w:hyperlink')
    h.set(qn('r:id'), rid)
    r = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    col = OxmlElement('w:color')
    col.set(qn('w:val'), '1F5FA8')
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rpr.append(col)
    rpr.append(u)
    r.append(rpr)
    t = OxmlElement('w:t')
    t.text = texto
    r.append(t)
    h.append(r)
    par._p.append(h)


# ---------------- Portada ----------------
titulo = doc.add_paragraph()
titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = titulo.add_run('Caso «El mercado de La Parada»\nMayorista Seguro: solución DevSecOps')
r.bold = True
r.font.size = Pt(22)
r.font.color.rgb = VERDE
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.add_run('Informe de la práctica · Preguntas 1 a 4\nMaylor Villar Rosado · 21 de noviembre de 2026').font.size = Pt(12)
doc.add_paragraph()

doc.add_heading('Enlaces de la entrega', level=2)
for nombre, url in ENLACES.items():
    par = doc.add_paragraph(style='List Bullet')
    par.add_run(nombre + ': ').bold = True
    enlace(par, url, url)
p('Cuentas de demostración de la aplicación (contraseña Demo2026!): admin@mayorista.pe (administración del mercado), '
  'inspector@mayorista.pe (inspector sanitario) y comerciante@mayorista.pe (comerciante). Las tarifas y la denuncia '
  'anónima se usan sin iniciar sesión.')
p('Código fuente completo adjunto en el archivo LaParada-DevSecOps.zip.')

doc.add_heading('Resumen de la solución', level=2)
p('La Parada concentraba la venta mayorista de alimentos pero también caos vehicular, insalubridad, comercio sin '
  'registro y el control de la estiba por grupos que cobraban cupos; el traslado a Santa Anita en 2012 terminó en '
  'enfrentamientos. Mayorista Seguro es una aplicación web que ordena el nuevo mercado atacando cada problema:')
tabla(['Problema del caso', 'Respuesta del sistema'], [
    ['Comercio sin registro', 'Padrón de comerciantes con RUC validado y asignación formal de puestos por pabellón'],
    ['Estiba controlada por grupos que cobran cupos', 'Estibadores con DNI y carnet; tarifa oficial pública; el sistema calcula el monto de cada servicio'],
    ['Caos vehicular', 'Reserva de franjas de descarga por zona con capacidad máxima y registro del ingreso en puerta'],
    ['Falta de salubridad', 'Inspecciones sanitarias por puesto (conforme, observado, clausurado)'],
    ['Violencia y miedo a denunciar', 'Denuncias anónimas con código de seguimiento, auditoría de todas las acciones e indicadores'],
], [5.5, 11])

# ---------------- Pregunta 1 ----------------
doc.add_page_break()
doc.add_heading('Pregunta 1 · Product Backlog y épicas en Jira', level=1)
p('El Product Backlog se construyó en Jira Software (proyecto Scrum, clave MS). Contiene 6 épicas y 24 historias de '
  'usuario, cada una vinculada a su épica, estimada en story points y priorizada con MoSCoW.')
doc.add_heading('Épicas', level=2)
tabla(['Épica', 'Descripción', 'Objetivo de negocio'],
      [[f"{e['id']} · {e['nombre']}", e['descripcion'], e['objetivo']] for e in BL['epicas']], [3.8, 6.4, 6.4], 8.5)
doc.add_heading('Técnicas de estimación y priorización', level=2)
viñetas([
    ('Estimación: ', 'planning poker con la serie de Fibonacci (1, 2, 3, 5, 8). Historia de referencia: HU13 «Consultar tarifas» = 2 puntos. '
     'Las historias de 8 puntos (HU17) son las de mayor incertidumbre (reglas de capacidad y franjas).'),
    ('Priorización: ', 'MoSCoW. En Jira se refleja en el campo Prioridad (Must = Highest, Should = High, Could = Medium, '
     'Won\'t = Low), en la etiqueta MoSCoW-* y en el orden (rank) del backlog. Criterio: primero lo que ataca la raíz del '
     'conflicto (identidad, padrón, estiba sin cupos), luego orden vehicular y salubridad, y al final lo deseable.'),
])
doc.add_heading('Historias de usuario', level=2)
p('Todas siguen el formato «Como [rol], quiero [acción], para [beneficio]» y tienen criterios de aceptación Dado/Cuando/Entonces '
  'en su descripción de Jira. Resumen:')
orden_m = {'Must': 0, 'Should': 1, 'Could': 2, "Won't": 3}
filas = []
for h in sorted(BL['historias'], key=lambda x: (orden_m[x['moscow']], x['id'])):
    filas.append([h['id'], h['epica'], f"Como {h['como']}, quiero {h['quiero']}, para {h['para']}.", h['sp'], h['moscow']])
tabla(['ID', 'Épica', 'Historia de usuario', 'SP', 'MoSCoW'], filas, [1.2, 1.1, 11.6, 0.9, 1.7], 8)
tabla(['Prioridad MoSCoW', 'Historias', 'Story points'], [
    [m, sum(1 for h in BL['historias'] if h['moscow'] == m), sum(h['sp'] for h in BL['historias'] if h['moscow'] == m)]
    for m in ['Must', 'Should', 'Could', "Won't"]] + [['Total', len(BL['historias']), sum(h['sp'] for h in BL['historias'])]], [5, 4, 4])
doc.add_heading('Ejemplo de criterios de aceptación (HU17 · Reservar franja de descarga, 8 SP, Must)', level=3)
viñetas(next(h for h in BL['historias'] if h['id'] == 'HU17')['criterios'])
doc.add_heading('Evidencia en Jira', level=2)
imagen(EV / 'jira_backlog.jpg', 'Backlog en Jira con épica, estado y story points de cada historia')
imagen(EV / 'jira_cronograma_epicas.jpg', 'Cronograma de Jira con las 6 épicas y los sprints')
imagen(EV / 'jira_epica_MS-3.jpg', 'Épica E3 con descripción, objetivo de negocio, historias hijas y prioridad')
imagen(EV / 'jira_historia_MS-18.jpg', 'Historia HU17 con formato Como/quiero/para, criterios Dado/Cuando/Entonces, story points y épica')

# ---------------- Pregunta 2 ----------------
doc.add_page_break()
doc.add_heading('Pregunta 2 · Simulación de 4 sprints: burndown, Gantt y Kanban', level=1)
p('Se simuló la ejecución en 4 sprints de 2 semanas (10 días hábiles) del 28/09 al 20/11/2026. En Jira los sprints se '
  'crearon con su objetivo y fechas, se iniciaron y cerraron, y cada historia recorrió To Do → In Progress → In Review → Done. '
  'La simulación día por día (qué día empieza, pasa a revisión y termina cada historia) está en docs/planificacion/simulacion.py; '
  'de ella salen el burndown, el Gantt y los tableros, y el script verifica que nunca se superen los límites WIP ni se rompan dependencias.')
doc.add_heading('Planificación de sprints', level=2)
filas = []
for s in BL['sprints']:
    hs = [h for h in BL['historias'] if h['sprint'] == s['numero']]
    if s['numero'] == 4:
        hs = hs + [h for h in BL['historias'] if h['id'] == 'HU19']
    sp = sum(h['sp'] for h in hs)
    filas.append([f"Sprint {s['numero']}\n{s['inicio']} a {s['fin']}", s['objetivo'],
                  ', '.join(f"{h['id']} ({h['sp']})" for h in hs), sp])
tabla(['Sprint y duración', 'Sprint goal', 'Sprint backlog (historia y SP)', 'SP'], filas, [3.2, 6.2, 6.2, 1], 8.5)
doc.add_heading('Burndown y velocidad', level=2)
imagen(IMG / 'burndown_sprints.png', 'Burndown de historias por sprint: línea ideal vs. real')
tabla(['Sprint', 'Comprometido (SP)', 'Completado (SP)', 'Observación'], [
    ['1', 18, 18, 'Arranque lento (pipeline y login), se recupera al final'],
    ['2', 21, 21, 'Ritmo cercano al ideal'],
    ['3', 23, 20, 'Sobrecompromiso: HU19 (3 SP) queda en revisión y pasa al Sprint 4'],
    ['4', 21, 21, 'Incluye el arrastre de HU19; se cumple el objetivo'],
    ['Promedio', '20,75', '20', 'Velocidad media de 20 SP por sprint, útil para planificar el siguiente release'],
], [2, 3, 3, 8.5])
imagen(IMG / 'velocidad.png', 'Velocidad: comprometido vs. completado', 13)
imagen(IMG / 'burndown_release.png', 'Burndown del release (80 SP planificados)', 13)
doc.add_heading('Diagrama de Gantt', level=2)
p('Cronograma con épicas (barras gruesas) e historias con sus fechas reales de inicio y fin, dependencias fin → inicio '
  '(por ejemplo HU04 → HU05, HU14 → HU15, HU17 → HU18/HU19) e hitos al cierre de cada sprint (H1 a H4, salida a producción el 20/11).')
imagen(IMG / 'gantt.png', 'Diagrama de Gantt con dependencias e hitos')
doc.add_heading('Tablero Kanban', level=2)
p('Columnas To Do / In Progress / In Review / Done con límites WIP: In Progress máximo 3 e In Review máximo 2 '
  '(configurados en Jira). Abajo, el tablero de Jira a mitad de cada sprint y la vista de flujo diario de cada historia.')
for n in range(1, 5):
    imagen(EV / f'jira_kanban_sprint{n}_dia5.jpg', f'Tablero de Jira · Sprint {n}, día 5 (límites WIP visibles en las columnas)')
for n in range(1, 5):
    imagen(IMG / f'kanban_sprint{n}.png', f'Sprint {n}: tablero en los días 3, 6 y 10 y flujo diario de cada historia', 15)
imagen(IMG / 'flujo_acumulado.png', 'Diagrama de flujo acumulado de los 4 sprints')

# ---------------- Pregunta 3 ----------------
doc.add_page_break()
doc.add_heading('Pregunta 3 · Arquitectura lógica y stack DevSecOps', level=1)
doc.add_heading('Arquitectura lógica', level=2)
imagen(IMG / 'arquitectura.png', 'Arquitectura lógica de Mayorista Seguro')
viñetas([
    ('Frontend: ', 'página web estática (HTML, CSS y JavaScript sin frameworks) servida por la CDN de Vercel. Tiene una vista '
     'pública (tarifas oficiales, denuncia anónima, seguimiento) y un panel por rol. Construye la interfaz sin innerHTML y con '
     'una política CSP que solo permite recursos propios, para evitar XSS.'),
    ('Backend / API: ', 'API REST en Node.js 22 con Express 5, desplegada como función serverless en Vercel. Módulos: autenticación, '
     'padrón y puestos, estiba, reservas, inspecciones, denuncias, indicadores y auditoría. Antes de cada módulo pasan los '
     'controles transversales: helmet (cabeceras), límite de peticiones, verificación del JWT, autorización por rol y validación con zod.'),
    ('Base de datos: ', 'PostgreSQL. En la demo en la nube y en las pruebas se usa PostgreSQL en memoria (pg-mem) con datos semilla; '
     'el mismo SQL funciona en un PostgreSQL gestionado definiendo DATABASE_URL. Todas las consultas son parametrizadas.'),
    ('Autenticación: ', 'correo y contraseña (bcrypt) que generan un JWT HS256 de 8 horas; el secreto JWT_SECRET vive cifrado en Vercel. '
     'Tres roles con mínimo privilegio: admin, inspector y comerciante.'),
    ('Servicios externos: ', 'GitHub (código y Pull Requests), GitHub Actions (CI/CD), Vercel (hosting) y Jira (gestión ágil).'),
    ('Comunicación: ', 'navegador → HTTPS → CDN / función; frontend → API por REST/JSON con cabecera Authorization: Bearer; API → base de datos por SQL parametrizado.'),
])
doc.add_heading('Stack por fase del ciclo DevSecOps y seguridad integrada (shift-left)', level=2)
imagen(IMG / 'devsecops.png', 'Herramientas y controles de seguridad por fase')
tabla(['Fase', 'Herramienta', 'Control de seguridad'], [
    ['Plan', 'Jira Software', 'Historias de seguridad (login, roles, denuncia anónima, auditoría) y casos de abuso del caso como criterios de aceptación'],
    ['Code', 'Git, GitHub, ESLint', 'Validación de entradas, SQL parametrizado, sin eval ni innerHTML, revisión por Pull Request'],
    ['Build', 'GitHub Actions, npm ci', 'Instalación reproducible con lockfile; npm audit (SCA) y Dependabot'],
    ['Test', 'node:test + supertest', 'Pruebas de seguridad: token manipulado, 403 por rol, intento de inyección SQL, no revelar si el usuario existe'],
    ['Release', 'Pull Request test → main', 'CodeQL y Semgrep (SAST), Gitleaks (secretos), dependency review; no se fusiona si algo falla'],
    ['Deploy', 'Vercel CLI desde Actions', 'Token en GitHub Secrets, JWT_SECRET cifrado en Vercel, HTTPS y HSTS'],
    ['Operate', 'Vercel Functions', 'helmet/CSP, límite de peticiones (login 10 cada 15 min, denuncias 20 por hora), roles'],
    ['Monitor', 'Logs de Vercel, /api/salud, auditoría', 'Registro de cada acción, CodeQL semanal programado y alertas de Dependabot'],
], [2, 4, 10.5])
doc.add_heading('Justificación del stack y vínculo con el caso', level=2)
viñetas([
    ('Node.js + Express: ', 'un solo lenguaje (JavaScript) en frontend y backend, ligero y conocido; permite entregar rápido el MVP que exige la urgencia del traslado.'),
    ('PostgreSQL: ', 'los datos del mercado son relacionales (comerciante–puesto–servicio–reserva) y necesitan integridad (RUC y DNI únicos, claves foráneas) para que no haya padrones paralelos.'),
    ('JWT con roles: ', 'separa lo que hace la municipalidad, el inspector y el comerciante; nadie puede alterar tarifas ni inspecciones ajenas.'),
    ('Denuncia anónima y límite de peticiones: ', 'el caso tuvo violencia y extorsión: el sistema no guarda la identidad del denunciante y evita abusos del formulario.'),
    ('Auditoría: ', 'en un entorno de conflicto, cada cambio queda con usuario y fecha para resolver disputas.'),
    ('Vercel + GitHub Actions: ', 'despliegue en la nube sin servidores que administrar, gratuito para el piloto y con HTTPS; GitHub Actions automatiza pruebas y seguridad en cada cambio.'),
    ('CodeQL, Semgrep, Gitleaks y npm audit: ', 'herramientas gratuitas para repositorios públicos que cubren el código propio, las dependencias y los secretos, que son los tres frentes por donde un sistema municipal expuesto podría ser atacado.'),
])

# ---------------- Pregunta 4 ----------------
doc.add_page_break()
doc.add_heading('Pregunta 4 · GitHub, pipeline CI/CD y despliegue en la nube', level=1)
doc.add_heading('Estrategia de ramas', level=2)
viñetas([
    ('main: ', 'producción. Solo recibe cambios por Pull Request desde test con el pipeline en verde; cada push despliega a producción.'),
    ('test: ', 'rama de pruebas e integración. Cada push ejecuta el pipeline completo y despliega una vista previa (preview) en Vercel.'),
    ('feature/*: ', 'trabajo de cada historia; se integra en test.'),
    ('Commits: ', 'mensajes descriptivos con el formato de Conventional Commits (feat, fix, test, ci, docs, chore).'),
])
imagen(EV / 'gh_commits.jpg', 'Historial de commits descriptivos')
imagen(EV / 'gh_branches.jpg', 'Ramas main y test')
imagen(EV / 'gh_pr.jpg', 'Pull Request de test hacia main con los checks del pipeline')
doc.add_heading('Pipeline CI/CD (.github/workflows/ci-cd.yml)', level=2)
tabla(['Etapa', 'Qué hace', 'Falla si…'], [
    ['1 · Build y lint', 'npm ci con lockfile, ESLint (no-eval, no-implied-eval) y verificación de build', 'hay errores de sintaxis o de estilo, o falta un archivo'],
    ['2 · Pruebas', '32 pruebas de integración con cobertura; reporte JUnit como artefacto y resumen en el job', 'alguna prueba falla'],
    ['3 · Seguridad', 'npm audit (SCA), Gitleaks (secretos en todo el historial), Semgrep (SAST); en PR, dependency review', 'hay vulnerabilidades altas, secretos o hallazgos SAST de severidad media o alta'],
    ['3b · CodeQL', 'Workflow aparte con consultas security-extended en cada push, PR y cada lunes', 'CodeQL encuentra vulnerabilidades'],
    ['4 · Deploy', 'Vercel CLI: test → preview, main → producción; prueba de humo de /, /api/salud y /api/tarifas', 'el despliegue o la prueba de humo fallan'],
], [3, 8, 5.5])
imagen(EV / 'gh_run_main.jpg', 'Ejecución exitosa del pipeline en main (build, pruebas, seguridad y deploy)')
imagen(EV / 'gh_run_test.jpg', 'Ejecución exitosa del pipeline en test')
imagen(EV / 'gh_codeql.jpg', 'Ejecuciones de CodeQL')
doc.add_heading('Pruebas automatizadas', level=2)
p('32 pruebas (node:test + supertest) agrupadas por épica; en el pipeline pasan las 32 y la cobertura total de líneas es 94,75 %. Incluyen pruebas funcionales '
  '(capacidad por franja, cálculo del monto con la tarifa oficial, doble asignación de puestos) y de seguridad (token '
  'manipulado, 401/403 por rol, inyección SQL en el código de seguimiento, mensajes que no revelan si un usuario existe).')
imagen(EV / 'gh_resumen_pruebas.png', 'Salida del job de pruebas en GitHub Actions: 32 pruebas aprobadas y reporte de cobertura', 14)
doc.add_heading('Seguridad implementada', level=2)
viñetas([
    ('SAST: ', 'CodeQL (security-extended) y Semgrep (reglas javascript, nodejsscan, expressjs y secrets).'),
    ('Análisis de dependencias: ', 'npm audit con nivel alto, dependency review en cada PR y Dependabot semanal (abre PRs de actualización hacia test).'),
    ('Escaneo de secretos: ', 'Gitleaks sobre todo el historial; los secretos reales (token de Vercel, JWT_SECRET) solo viven en GitHub Secrets y en Vercel.'),
    ('En la aplicación: ', 'helmet con CSP, HSTS y frame-ancestors none; límite de peticiones; bcrypt; JWT con algoritmo fijo; validación zod; SQL parametrizado; errores sin detalles internos.'),
])
doc.add_heading('Hallazgos reales de los controles y su corrección', level=3)
tabla(['Control', 'Hallazgo', 'Corrección'], [
    ['npm audit (SCA)', 'Vulnerabilidad alta en zod 3 (GHSA-mrhx-c7xc-m3w5): consumo de memoria al validar colecciones grandes', 'Actualización a zod 4; npm audit queda en 0 vulnerabilidades'],
    ['Semgrep (SAST)', 'Posible ReDoS: expresión regular aplicada a un parámetro de la URL', 'El filtro de fecha se valida con zod'],
    ['CodeQL (SAST)', '2 alertas js/missing-rate-limiting: rutas con autorización sin límite de peticiones', 'Límite general de 300 solicitudes cada 15 minutos (rama feature/limite-general, PR #9 a test y PR #10 a main); alertas cerradas como corregidas'],
], [3, 7, 6.5])
imagen(EV / 'gh_pr_feature.jpg', 'PR #9 de feature/limite-general hacia test con la corrección de CodeQL')
doc.add_heading('Solución desplegada', level=2)
par = doc.add_paragraph()
par.add_run('URL pública: ').bold = True
enlace(par, ENLACES['Solución desplegada (Vercel)'], ENLACES['Solución desplegada (Vercel)'])
imagen(EV / 'app_publica.png', 'Vista pública: tarifas oficiales, ingreso y denuncia anónima')
imagen(EV / 'app_indicadores.png', 'Panel del administrador: indicadores')
imagen(EV / 'app_estiba.png', 'Estiba formal: estibadores con carnet y servicios con tarifa oficial')
imagen(EV / 'app_reservas.png', 'Reservas de franjas de descarga')

salida = RAIZ / 'Informe_LaParada_DevSecOps.docx'
doc.save(salida)
print('Informe en', salida)
