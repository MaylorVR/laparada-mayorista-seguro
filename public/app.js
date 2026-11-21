'use strict';

(function () {
  const $ = (sel) => document.querySelector(sel);
  let token = sessionStorage.getItem('token') || '';
  let usuario = JSON.parse(sessionStorage.getItem('usuario') || 'null');

  function aviso(msg) {
    const el = $('#aviso');
    el.textContent = msg;
    el.classList.add('ver');
    clearTimeout(aviso.t);
    aviso.t = setTimeout(() => el.classList.remove('ver'), 3500);
  }

  async function api(ruta, opciones = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;
    const res = await fetch('/api' + ruta, { ...opciones, headers });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && token) cerrarSesion();
    if (!res.ok) {
      const det = data.detalles ? ': ' + data.detalles.map((d) => d.mensaje).join(', ') : '';
      throw new Error((data.error || 'Error') + det);
    }
    return data;
  }

  // Construye elementos sin innerHTML para evitar XSS.
  function el(tag, attrs = {}, ...hijos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v === true ? '' : v);
    }
    for (const h of hijos.flat()) {
      if (h === null || h === undefined) continue;
      e.append(h instanceof Node ? h : document.createTextNode(String(h)));
    }
    return e;
  }

  function tabla(columnas, filas) {
    return el('div', { class: 'tabla-scroll' },
      el('table', {},
        el('thead', {}, el('tr', {}, columnas.map((c) => el('th', {}, c[0])))),
        el('tbody', {}, filas.length
          ? filas.map((f) => el('tr', {}, columnas.map((c) => el('td', {}, c[1](f)))))
          : el('tr', {}, el('td', { colspan: columnas.length }, 'Sin registros')))));
  }

  function datosForm(form, numeros = []) {
    const d = {};
    for (const [k, v] of new FormData(form).entries()) {
      if (v === '') continue;
      d[k] = numeros.includes(k) ? Number(v) : v;
    }
    return d;
  }

  function campo(etiqueta, nombre, extra = {}) {
    return el('label', {}, etiqueta, el('input', { name: nombre, ...extra }));
  }
  function selector(etiqueta, nombre, opciones) {
    return el('label', {}, etiqueta,
      el('select', { name: nombre }, opciones.map(([v, t]) => el('option', { value: v }, t))));
  }

  function formulario(campos, textoBoton, alEnviar, numeros = []) {
    const f = el('form', { class: 'fila' }, campos, el('button', { type: 'submit' }, textoBoton));
    f.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      try {
        await alEnviar(datosForm(f, numeros));
        f.reset();
        aviso('Guardado');
        mostrar(actual);
      } catch (e) { aviso(e.message); }
    });
    return f;
  }

  const fecha = (v) => (v ? new Date(v).toLocaleString('es-PE') : '—');
  const hoy = () => new Date().toISOString().slice(0, 10);
  const esAdmin = () => usuario && usuario.rol === 'admin';

  // ---------- Vistas privadas ----------
  const vistas = {
    async Indicadores() {
      const k = await api('/indicadores');
      const nombres = {
        comerciantes_formalizados: 'Comerciantes formalizados',
        puestos_asignados: 'Puestos asignados',
        estibadores_con_carnet: 'Estibadores con carnet',
        servicios_estiba: 'Servicios de estiba con tarifa oficial',
        reservas_descarga: 'Reservas de descarga',
        inspecciones_observadas: 'Inspecciones observadas',
        denuncias_abiertas: 'Denuncias abiertas',
      };
      return el('div', { class: 'kpis' },
        Object.entries(k).map(([key, v]) => el('div', { class: 'kpi' }, el('b', {}, v), el('span', {}, nombres[key] || key))));
    },

    async Comerciantes() {
      const lista = await api('/comerciantes');
      return el('div', {},
        esAdmin() ? el('article', { class: 'card' }, el('h2', {}, 'Registrar comerciante'),
          formulario([
            campo('RUC', 'ruc', { required: true, pattern: '(10|20)[0-9]{9}' }),
            campo('Razón social', 'razon_social', { required: true }),
            selector('Rubro', 'rubro', [['frutas', 'Frutas'], ['verduras', 'Verduras'], ['tuberculos', 'Tubérculos'], ['abarrotes', 'Abarrotes']]),
            campo('Celular', 'telefono', { pattern: '9[0-9]{8}' }),
          ], 'Registrar', (d) => api('/comerciantes', { method: 'POST', body: JSON.stringify(d) }))) : null,
        el('article', { class: 'card' }, el('h2', {}, 'Padrón de comerciantes'),
          tabla([['ID', (c) => c.id], ['RUC', (c) => c.ruc], ['Razón social', (c) => c.razon_social], ['Rubro', (c) => c.rubro], ['Estado', (c) => c.estado]], lista)));
    },

    async Puestos() {
      const lista = await api('/puestos');
      return el('div', {},
        esAdmin() ? el('article', { class: 'card' }, el('h2', {}, 'Crear puesto'),
          formulario([
            campo('Código', 'codigo', { required: true, placeholder: 'A-103' }),
            campo('Pabellón', 'pabellon', { required: true, maxlength: 1, placeholder: 'A' }),
            campo('ID comerciante (opcional)', 'comerciante_id', { type: 'number', min: 1 }),
          ], 'Crear', (d) => api('/puestos', { method: 'POST', body: JSON.stringify(d) }), ['comerciante_id'])) : null,
        el('article', { class: 'card' }, el('h2', {}, 'Puestos'),
          tabla([['ID', (p) => p.id], ['Código', (p) => p.codigo], ['Pabellón', (p) => p.pabellon], ['Comerciante', (p) => p.razon_social || 'Libre']], lista)));
    },

    async Estiba() {
      const [est, serv, tar] = await Promise.all([api('/estibadores'), api('/servicios-estiba'), api('/tarifas')]);
      const puedeRegistrar = usuario.rol === 'admin' || usuario.rol === 'comerciante';
      return el('div', {},
        esAdmin() ? el('article', { class: 'card' }, el('h2', {}, 'Registrar estibador'),
          formulario([campo('DNI', 'dni', { required: true, pattern: '[0-9]{8}' }), campo('Nombre', 'nombre', { required: true })],
            'Registrar', (d) => api('/estibadores', { method: 'POST', body: JSON.stringify(d) }))) : null,
        puedeRegistrar ? el('article', { class: 'card' }, el('h2', {}, 'Registrar servicio de estiba'),
          el('p', { class: 'nota' }, 'El monto lo calcula el sistema con la tarifa oficial.'),
          formulario([
            selector('Estibador', 'estibador_id', est.filter((e) => e.carnet_activo).map((e) => [e.id, e.nombre])),
            campo('ID comerciante', 'comerciante_id', { type: 'number', min: 1, required: true }),
            selector('Carga', 'tipo_carga', tar.map((t) => [t.tipo_carga, `${t.tipo_carga} (S/ ${t.precio_unitario.toFixed(2)})`])),
            campo('Cantidad', 'cantidad', { type: 'number', min: 1, required: true }),
          ], 'Registrar', (d) => api('/servicios-estiba', { method: 'POST', body: JSON.stringify(d) }), ['estibador_id', 'comerciante_id', 'cantidad'])) : null,
        el('article', { class: 'card' }, el('h2', {}, 'Estibadores'),
          tabla([['ID', (e) => e.id], ['DNI', (e) => e.dni], ['Nombre', (e) => e.nombre],
            ['Carnet', (e) => el('span', { class: 'chip ' + (e.carnet_activo ? 'ok' : 'mal') }, e.carnet_activo ? 'Activo' : 'Suspendido')]], est)),
        el('article', { class: 'card' }, el('h2', {}, 'Servicios de estiba'),
          tabla([['Fecha', (s) => fecha(s.creado_en)], ['Estibador', (s) => s.estibador], ['Comerciante', (s) => s.comerciante],
            ['Carga', (s) => `${s.cantidad} × ${s.tipo_carga}`], ['Monto S/', (s) => s.monto.toFixed(2)]], serv)));
    },

    async Reservas() {
      const lista = await api('/reservas');
      const puedeReservar = usuario.rol === 'admin' || usuario.rol === 'comerciante';
      return el('div', {},
        puedeReservar ? el('article', { class: 'card' }, el('h2', {}, 'Reservar franja de descarga'),
          el('p', { class: 'nota' }, 'Cada zona admite un número limitado de camiones por hora para evitar el caos vehicular.'),
          formulario([
            campo('Placa', 'placa', { required: true, placeholder: 'ABC-123' }),
            campo('ID comerciante', 'comerciante_id', { type: 'number', min: 1, required: true }),
            campo('Fecha', 'fecha', { type: 'date', required: true, value: hoy() }),
            selector('Franja', 'franja', ['02:00-03:00', '03:00-04:00', '04:00-05:00', '05:00-06:00', '06:00-07:00'].map((f) => [f, f])),
            selector('Zona', 'zona', [['Z1-Frutas', 'Z1 Frutas'], ['Z2-Verduras', 'Z2 Verduras'], ['Z3-Tuberculos', 'Z3 Tubérculos']]),
          ], 'Reservar', (d) => api('/reservas', { method: 'POST', body: JSON.stringify(d) }), ['comerciante_id'])) : null,
        el('article', { class: 'card' }, el('h2', {}, 'Reservas'),
          tabla([['Fecha', (r) => r.fecha], ['Franja', (r) => r.franja], ['Zona', (r) => r.zona], ['Placa', (r) => r.placa],
            ['Estado', (r) => r.estado],
            ['', (r) => (esAdmin() && r.estado === 'reservada'
              ? el('button', { class: 'sec', onclick: async () => {
                try { await api(`/reservas/${r.id}/ingreso`, { method: 'PATCH' }); aviso('Ingreso registrado'); mostrar(actual); } catch (e) { aviso(e.message); }
              } }, 'Registrar ingreso') : '')]], lista)));
    },

    async Inspecciones() {
      const [lista, puestos] = await Promise.all([api('/inspecciones'), api('/puestos')]);
      const puede = usuario.rol === 'inspector' || usuario.rol === 'admin';
      return el('div', {},
        puede ? el('article', { class: 'card' }, el('h2', {}, 'Registrar inspección sanitaria'),
          formulario([
            selector('Puesto', 'puesto_id', puestos.map((p) => [p.id, p.codigo])),
            selector('Resultado', 'resultado', [['conforme', 'Conforme'], ['observado', 'Observado'], ['clausurado', 'Clausurado']]),
            campo('Observaciones', 'observaciones', { maxlength: 500 }),
          ], 'Registrar', (d) => api('/inspecciones', { method: 'POST', body: JSON.stringify(d) }), ['puesto_id'])) : null,
        el('article', { class: 'card' }, el('h2', {}, 'Inspecciones'),
          tabla([['Fecha', (i) => fecha(i.creado_en)], ['Puesto', (i) => i.puesto], ['Inspector', (i) => i.inspector],
            ['Resultado', (i) => el('span', { class: 'chip ' + (i.resultado === 'conforme' ? 'ok' : 'mal') }, i.resultado)],
            ['Observaciones', (i) => i.observaciones || '']], lista)));
    },

    async Denuncias() {
      const lista = await api('/denuncias');
      return el('article', { class: 'card' }, el('h2', {}, 'Denuncias recibidas'),
        tabla([['Código', (d) => d.codigo], ['Tipo', (d) => d.tipo], ['Descripción', (d) => d.descripcion], ['Lugar', (d) => d.ubicacion || ''],
          ['Estado', (d) => {
            const s = el('select', {}, ['recibida', 'en_investigacion', 'derivada_pnp', 'cerrada'].map((x) => el('option', { value: x, selected: x === d.estado }, x)));
            s.addEventListener('change', async () => {
              try { await api(`/denuncias/${d.id}`, { method: 'PATCH', body: JSON.stringify({ estado: s.value }) }); aviso('Estado actualizado'); } catch (e) { aviso(e.message); }
            });
            return s;
          }]], lista));
    },

    async Auditoria() {
      const lista = await api('/auditoria');
      return el('article', { class: 'card' }, el('h2', {}, 'Auditoría (últimas 100 acciones)'),
        tabla([['Fecha', (a) => fecha(a.creado_en)], ['Usuario', (a) => a.usuario_id], ['Acción', (a) => a.accion], ['Entidad', (a) => `${a.entidad} #${a.entidad_id}`]], lista));
    },
  };

  let actual = 'Indicadores';
  async function mostrar(nombre) {
    actual = nombre;
    document.querySelectorAll('#tabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.v === nombre)));
    const cont = $('#contenido');
    try {
      cont.replaceChildren(await vistas[nombre]());
    } catch (e) {
      cont.replaceChildren(el('p', {}, e.message));
    }
  }

  function pintarSesion() {
    const s = $('#sesion');
    if (!usuario) {
      s.replaceChildren();
      $('#vista-publica').hidden = false;
      $('#vista-privada').hidden = true;
      return;
    }
    s.replaceChildren(el('span', {}, `${usuario.nombre} (${usuario.rol})`),
      el('button', { class: 'sec', onclick: cerrarSesion }, 'Salir'));
    $('#vista-publica').hidden = true;
    $('#vista-privada').hidden = false;
    const nombres = ['Indicadores', 'Comerciantes', 'Puestos', 'Estiba', 'Reservas', 'Inspecciones'];
    if (esAdmin()) nombres.push('Denuncias', 'Auditoria');
    $('#tabs').replaceChildren(...nombres.map((n) => el('button', { 'data-v': n, role: 'tab', onclick: () => mostrar(n) }, n === 'Auditoria' ? 'Auditoría' : n)));
    mostrar('Indicadores');
  }

  function cerrarSesion() {
    token = '';
    usuario = null;
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('usuario');
    pintarSesion();
  }

  // ---------- Vista pública ----------
  async function cargarTarifas() {
    try {
      const t = await api('/tarifas');
      $('#tabla-tarifas').replaceChildren(...t.map((x) => el('tr', {}, el('td', {}, x.tipo_carga), el('td', {}, x.descripcion), el('td', {}, x.precio_unitario.toFixed(2)))));
    } catch (e) { aviso(e.message); }
  }

  $('#form-login').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const r = await api('/auth/login', { method: 'POST', body: JSON.stringify(datosForm(ev.target)) });
      token = r.token;
      usuario = r.usuario;
      sessionStorage.setItem('token', token);
      sessionStorage.setItem('usuario', JSON.stringify(usuario));
      ev.target.reset();
      pintarSesion();
    } catch (e) { aviso(e.message); }
  });

  $('#form-denuncia').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      const r = await api('/denuncias', { method: 'POST', body: JSON.stringify(datosForm(ev.target)) });
      ev.target.reset();
      aviso('Denuncia registrada. Guarde su código: ' + r.codigo);
      $('#form-seguimiento').codigo.value = r.codigo;
    } catch (e) { aviso(e.message); }
  });

  $('#form-seguimiento').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const out = $('#res-seguimiento');
    try {
      const r = await api('/denuncias/seguimiento/' + encodeURIComponent(ev.target.codigo.value.trim()));
      out.replaceChildren(el('p', {}, `${r.codigo}: ${r.tipo} — estado `, el('b', {}, r.estado)));
    } catch (e) { out.replaceChildren(el('p', {}, e.message)); }
  });

  cargarTarifas();
  pintarSesion();
})();
