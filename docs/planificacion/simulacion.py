"""Simulación de la ejecución de 4 sprints del proyecto Mayorista Seguro.

Lee backlog.json y define, para cada historia, el día hábil del sprint (1-10) en que
pasó a In Progress, a In Review y a Done. Con eso se calculan burndown, velocidad,
flujo Kanban (respetando límites WIP) y el cronograma para el Gantt.
"""
import json
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).parent
BACKLOG = json.loads((AQUI / 'backlog.json').read_text(encoding='utf-8'))

WIP = {'In Progress': 3, 'In Review': 2}
DIAS_SPRINT = 10

# historia: (sprint, día inicio, día a revisión, día done | None si no terminó en ese sprint)
FLUJO = {
    1: {'HU01': (1, 3, 4), 'HU04': (1, 4, 5), 'HU05': (5, 7, 8), 'HU10': (5, 9, 10)},
    2: {'HU11': (1, 2, 3), 'HU02': (1, 3, 4), 'HU13': (2, 4, 4), 'HU14': (4, 5, 6),
        'HU12': (5, 6, 7), 'HU15': (6, 8, 10)},
    3: {'HU06': (1, 4, 5), 'HU17': (1, 6, 7), 'HU07': (5, 6, 7), 'HU18': (7, 8, 9),
        'HU16': (7, 8, 9), 'HU19': (8, 10, None)},
    4: {'HU19': (1, 2, 2), 'HU20': (1, 4, 5), 'HU03': (2, 4, 5), 'HU21': (5, 6, 6),
        'HU09': (6, 7, 8), 'HU08': (7, 8, 9), 'HU22': (8, 9, 10)},
}

HIST = {h['id']: h for h in BACKLOG['historias']}
EPICAS = {e['id']: e for e in BACKLOG['epicas']}
SPRINTS = {s['numero']: s for s in BACKLOG['sprints']}


def dias_habiles(sprint):
    s = SPRINTS[sprint]
    d = date.fromisoformat(s['inicio'])
    fin = date.fromisoformat(s['fin'])
    dias = []
    while d <= fin:
        if d.weekday() < 5:
            dias.append(d)
        d += timedelta(days=1)
    assert len(dias) == DIAS_SPRINT, (sprint, len(dias))
    return dias


def compromiso(sprint):
    return {hid: HIST[hid]['sp'] for hid in FLUJO[sprint]}


def burndown(sprint):
    """Puntos restantes al final de cada día (índice 0 = inicio del sprint)."""
    comp = compromiso(sprint)
    total = sum(comp.values())
    real = [total]
    for dia in range(1, DIAS_SPRINT + 1):
        hechos = sum(comp[h] for h, (_, _, done) in FLUJO[sprint].items() if done and done <= dia)
        real.append(total - hechos)
    ideal = [total - total * i / DIAS_SPRINT for i in range(DIAS_SPRINT + 1)]
    return total, ideal, real


def velocidad(sprint):
    comp = compromiso(sprint)
    hechos = sum(comp[h] for h, (_, _, done) in FLUJO[sprint].items() if done)
    return sum(comp.values()), hechos


def estado(sprint, hid, dia):
    ini, rev, done = FLUJO[sprint][hid]
    if done and dia >= done:
        return 'Done'
    if dia >= rev:
        return 'In Review'
    if dia >= ini:
        return 'In Progress'
    return 'To Do'


def tablero(sprint, dia):
    cols = {'To Do': [], 'In Progress': [], 'In Review': [], 'Done': []}
    for hid in FLUJO[sprint]:
        cols[estado(sprint, hid, dia)].append(hid)
    return cols


def verificar_wip():
    for sp in FLUJO:
        for dia in range(1, DIAS_SPRINT + 1):
            t = tablero(sp, dia)
            for col, lim in WIP.items():
                assert len(t[col]) <= lim, f'WIP excedido sprint {sp} día {dia} {col}: {t[col]}'


def fechas_historia(hid):
    """Primera fecha de inicio y fecha de término real (considera arrastre)."""
    tramos = [(sp, FLUJO[sp][hid]) for sp in FLUJO if hid in FLUJO[sp]]
    sp0, (ini, _, _) = tramos[0]
    inicio = dias_habiles(sp0)[ini - 1]
    spn, (_, rev, done) = tramos[-1]
    fin = dias_habiles(spn)[(done or rev) - 1]
    return inicio, fin, [sp for sp, _ in tramos]


DEPENDENCIAS = [
    ('HU01', 'HU02'), ('HU02', 'HU03'), ('HU04', 'HU05'), ('HU05', 'HU09'),
    ('HU10', 'HU12'), ('HU11', 'HU12'), ('HU13', 'HU15'), ('HU14', 'HU15'),
    ('HU14', 'HU16'), ('HU06', 'HU07'), ('HU06', 'HU08'), ('HU17', 'HU18'),
    ('HU17', 'HU19'), ('HU11', 'HU20'), ('HU20', 'HU21'), ('HU20', 'HU22'),
]

HITOS = [
    (date(2026, 10, 9), 'H1 · Base segura y padrón (fin S1)'),
    (date(2026, 10, 23), 'H2 · Estiba formal operativa (fin S2)'),
    (date(2026, 11, 6), 'H3 · Reservas y denuncias (fin S3)'),
    (date(2026, 11, 20), 'H4 · Salida a producción (fin S4)'),
]

if __name__ == '__main__':
    verificar_wip()
    for sp in FLUJO:
        c, h = velocidad(sp)
        print(f'Sprint {sp}: comprometido {c} SP, completado {h} SP')
    for a, b in DEPENDENCIAS:
        fa = fechas_historia(a)[1]
        fb = fechas_historia(b)[0]
        assert fa <= fb, f'dependencia rota {a}->{b}: {fa} > {fb}'
    print('WIP y dependencias OK')
