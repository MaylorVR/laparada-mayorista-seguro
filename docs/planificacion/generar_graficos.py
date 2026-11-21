"""Genera burndown, velocidad, flujo acumulado y Gantt (PNG) a partir de la simulación."""
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

import simulacion as sim  # noqa: E402

SALIDA = Path(__file__).parent.parent / 'img'
SALIDA.mkdir(exist_ok=True)

TINTA = '#1f2a24'
GRIS = '#8a948e'
IDEAL = '#9aa5a0'
REAL = '#2f6b3f'
ACENTO = '#d98a1f'
COLORES_EPICA = {'E1': '#2f6b3f', 'E2': '#d98a1f', 'E3': '#3d6fa8', 'E4': '#8c4f9e', 'E5': '#b23a2b', 'E6': '#5c6b63'}

plt.rcParams.update({
    'font.family': 'Segoe UI', 'font.size': 10, 'axes.edgecolor': '#c9cfca',
    'axes.labelcolor': TINTA, 'xtick.color': TINTA, 'ytick.color': TINTA,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
    'grid.color': '#e8ebe8', 'grid.linewidth': 0.8,
})


def burndown_ax(ax, sp):
    total, ideal, real = sim.burndown(sp)
    x = list(range(sim.DIAS_SPRINT + 1))
    ax.plot(x, ideal, ls='--', color=IDEAL, lw=1.8, label='Ideal')
    ax.plot(x, real, color=REAL, lw=2.4, marker='o', ms=4, label='Real')
    comp, hecho = sim.velocidad(sp)
    if real[-1] > 0:
        ax.annotate(f'{real[-1]} SP sin terminar\n(HU19 pasa al Sprint 4)', xy=(10, real[-1]), xytext=(0.6, 3.5),
                    arrowprops=dict(arrowstyle='->', color=ACENTO), color=ACENTO, fontsize=9)
    s = sim.SPRINTS[sp]
    ax.set_title(f"Sprint {sp} · {s['inicio'][5:]} a {s['fin'][5:]} · velocidad {hecho}/{comp} SP", fontsize=10.5, color=TINTA, loc='left')
    ax.set_xticks(x)
    ax.set_xlabel('Día hábil del sprint')
    ax.set_ylabel('Story points restantes')
    ax.set_ylim(0, total + 2)
    ax.legend(frameon=False, loc='upper right')


def graficos_burndown():
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    for sp, ax in zip(sim.FLUJO, axs.flat):
        burndown_ax(ax, sp)
    fig.suptitle('Burndown de historias de usuario por sprint (ideal vs. real)', fontsize=14, color=TINTA, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(SALIDA / 'burndown_sprints.png', dpi=160)
    plt.close(fig)
    for sp in sim.FLUJO:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        burndown_ax(ax, sp)
        fig.tight_layout()
        fig.savefig(SALIDA / f'burndown_sprint{sp}.png', dpi=160)
        plt.close(fig)


def grafico_velocidad():
    sps = list(sim.FLUJO)
    comp = [sim.velocidad(s)[0] for s in sps]
    hecho = [sim.velocidad(s)[1] for s in sps]
    prom = sum(hecho) / len(hecho)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    w = 0.36
    b1 = ax.bar([s - w / 2 for s in sps], comp, w, color='#c9d8cd', label='Comprometido')
    b2 = ax.bar([s + w / 2 for s in sps], hecho, w, color=REAL, label='Completado')
    ax.bar_label(b1, padding=2, color=GRIS)
    ax.bar_label(b2, padding=2, color=TINTA, fontweight='bold')
    ax.axhline(prom, color=ACENTO, ls='--', lw=1.5)
    ax.text(4.45, prom + 0.4, f'Velocidad promedio {prom:.0f} SP', color=ACENTO, ha='right')
    ax.set_xticks(sps, [f'Sprint {s}' for s in sps])
    ax.set_ylabel('Story points')
    ax.set_ylim(0, max(comp) + 5)
    ax.grid(axis='x', visible=False)
    ax.legend(frameon=False, loc='upper left')
    ax.set_title('Velocidad del equipo por sprint', loc='left', fontsize=13, color=TINTA)
    fig.tight_layout()
    fig.savefig(SALIDA / 'velocidad.png', dpi=160)
    plt.close(fig)


def grafico_release():
    total = sum(h['sp'] for h in sim.BACKLOG['historias'] if h['sprint'])
    restantes = [total]
    for sp in sim.FLUJO:
        restantes.append(restantes[-1] - sim.velocidad(sp)[1])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = list(range(len(restantes)))
    ax.plot(x, [total - total * i / 4 for i in x], ls='--', color=IDEAL, label='Ideal')
    ax.plot(x, restantes, color=REAL, marker='o', lw=2.4, label='Real')
    for i, r in zip(x, restantes):
        ax.annotate(str(r), (i, r), textcoords='offset points', xytext=(6, 6), color=TINTA)
    ax.set_xticks(x, ['Inicio'] + [f'Fin S{s}' for s in sim.FLUJO])
    ax.set_ylabel('Story points restantes del release')
    ax.legend(frameon=False)
    ax.set_title('Burndown del release (80 SP planificados)', loc='left', fontsize=13, color=TINTA)
    fig.tight_layout()
    fig.savefig(SALIDA / 'burndown_release.png', dpi=160)
    plt.close(fig)


def grafico_cfd():
    fechas, series = [], {c: [] for c in ['Done', 'In Review', 'In Progress', 'To Do']}
    for sp in sim.FLUJO:
        dias = sim.dias_habiles(sp)
        for i, d in enumerate(dias, start=1):
            fechas.append(d)
            t = sim.tablero(sp, i)
            hechos_previos = sum(sim.velocidad(s)[1] for s in sim.FLUJO if s < sp)
            for col in series:
                pts = sum(sim.HIST[h]['sp'] for h in t[col])
                series[col].append(pts + (hechos_previos if col == 'Done' else 0))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    colores = {'Done': REAL, 'In Review': ACENTO, 'In Progress': '#3d6fa8', 'To Do': '#d5dad6'}
    ax.stackplot(fechas, *[series[c] for c in series], labels=list(series), colors=[colores[c] for c in series], step='post')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.set_ylabel('Story points')
    ax.legend(loc='upper left', frameon=False, ncol=4)
    ax.set_title('Diagrama de flujo acumulado (CFD) del tablero Kanban', loc='left', fontsize=13, color=TINTA)
    fig.tight_layout()
    fig.savefig(SALIDA / 'flujo_acumulado.png', dpi=160)
    plt.close(fig)


def grafico_gantt():
    filas = []  # (etiqueta, inicio, fin, color, es_epica, id)
    orden_epicas = ['E6', 'E5', 'E1', 'E2', 'E3', 'E4']
    fechas_h = {h: sim.fechas_historia(h) for sp in sim.FLUJO for h in sim.FLUJO[sp]}
    for e in orden_epicas:
        hs = [h for h in fechas_h if sim.HIST[h]['epica'] == e]
        hs.sort(key=lambda h: fechas_h[h][0])
        ini = min(fechas_h[h][0] for h in hs)
        fin = max(fechas_h[h][1] for h in hs)
        filas.append((f"{e} · {sim.EPICAS[e]['nombre']}", ini, fin, COLORES_EPICA[e], True, e))
        for h in hs:
            filas.append((f"   {h} {sim.HIST[h]['titulo']}", fechas_h[h][0], fechas_h[h][1], COLORES_EPICA[e], False, h))

    fig, ax = plt.subplots(figsize=(15, 11))
    y_de = {}
    for i, (etq, ini, fin, color, epica, ident) in enumerate(filas):
        y = len(filas) - i
        y_de[ident] = y
        dur = (fin - ini).days + 1
        if epica:
            ax.barh(y, dur, left=mdates.date2num(ini), height=0.36, color=color, alpha=0.95)
        else:
            ax.barh(y, dur, left=mdates.date2num(ini), height=0.62, color=color, alpha=0.55, edgecolor=color)
    ax.set_yticks([len(filas) - i for i in range(len(filas))], [f[0] for f in filas])
    for lbl, f in zip(ax.get_yticklabels(), filas):
        if f[4]:
            lbl.set_fontweight('bold')

    for a, b in sim.DEPENDENCIAS:
        fa = mdates.date2num(fechas_h[a][1] + timedelta(days=1))
        fb = mdates.date2num(fechas_h[b][0])
        ax.annotate('', xy=(fb, y_de[b]), xytext=(fa, y_de[a]),
                    arrowprops=dict(arrowstyle='->', color='#6b756f', lw=0.9, connectionstyle='angle,angleA=0,angleB=90,rad=4'))

    for sp in sim.FLUJO:
        s = sim.SPRINTS[sp]
        ini = mdates.date2num(sim.dias_habiles(sp)[0])
        ax.axvspan(ini, mdates.date2num(sim.dias_habiles(sp)[-1]) + 1, color='#2f6b3f' if sp % 2 else '#d98a1f', alpha=0.05)
        ax.text(ini + 0.3, len(filas) + 1.1, f"Sprint {sp}", color=GRIS, fontsize=10, fontweight='bold')
    for d, nombre in sim.HITOS:
        x = mdates.date2num(d) + 1
        ax.scatter([x], [len(filas) + 0.4], marker='D', s=70, color=ACENTO, zorder=5)
        ax.axvline(x, color=ACENTO, lw=0.8, ls=':')
        ax.text(x - 0.25, len(filas) + 0.75, nombre.split(' · ')[0], ha='right', fontsize=9, color=ACENTO, fontweight='bold')
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker='D', ls='', color=ACENTO, label=n) for _, n in sim.HITOS]
              + [Line2D([], [], color='#6b756f', lw=1, marker='>', ms=4, label='Dependencia fin → inicio')],
              loc='lower left', frameon=True, framealpha=0.95, title='Hitos', fontsize=9)

    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.set_ylim(0, len(filas) + 1.8)
    ax.grid(axis='y', visible=False)
    ax.set_title('Diagrama de Gantt · épicas, historias, dependencias (flechas) e hitos (rombos)', loc='left', fontsize=14, color=TINTA)
    fig.tight_layout()
    fig.savefig(SALIDA / 'gantt.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    sim.verificar_wip()
    graficos_burndown()
    grafico_velocidad()
    grafico_release()
    grafico_cfd()
    grafico_gantt()
    print('Gráficos en', SALIDA)
