'use strict';

const { test, describe, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { app, db, request, login } = require('./helpers');

let admin;
let comerciante;
let inspector;
const auth = (t) => ({ Authorization: 'Bearer ' + t });

beforeEach(async () => {
  await db.reset();
  admin = await login('admin@mayorista.pe');
  comerciante = await login('comerciante@mayorista.pe');
  inspector = await login('inspector@mayorista.pe');
});

describe('Épica 1 · Padrón de comerciantes y puestos', () => {
  test('admin registra un comerciante formal', async () => {
    const r = await request(app).post('/api/comerciantes').set(auth(admin))
      .send({ ruc: '20999888777', razon_social: 'Mangos Piura SAC', rubro: 'frutas', telefono: '999111222' });
    assert.equal(r.status, 201);
    assert.equal(r.body.estado, 'formalizado');
  });

  test('RUC inválido es rechazado', async () => {
    const r = await request(app).post('/api/comerciantes').set(auth(admin))
      .send({ ruc: '123', razon_social: 'X', rubro: 'frutas' });
    assert.equal(r.status, 400);
  });

  test('RUC duplicado devuelve 409', async () => {
    const r = await request(app).post('/api/comerciantes').set(auth(admin))
      .send({ ruc: '20512345678', razon_social: 'Otra', rubro: 'frutas' });
    assert.equal(r.status, 409);
  });

  test('un comerciante no puede registrar comerciantes', async () => {
    const r = await request(app).post('/api/comerciantes').set(auth(comerciante))
      .send({ ruc: '20999888777', razon_social: 'X SAC', rubro: 'frutas' });
    assert.equal(r.status, 403);
  });

  test('asignar un puesto libre y no permitir doble asignación', async () => {
    const puestos = (await request(app).get('/api/puestos').set(auth(admin))).body;
    const libre = puestos.find((p) => !p.comerciante_id);
    const r1 = await request(app).patch(`/api/puestos/${libre.id}/asignar`).set(auth(admin)).send({ comerciante_id: 1 });
    assert.equal(r1.status, 200);
    const r2 = await request(app).patch(`/api/puestos/${libre.id}/asignar`).set(auth(admin)).send({ comerciante_id: 2 });
    assert.equal(r2.status, 409);
  });

  test('el código del puesto debe coincidir con el pabellón', async () => {
    const r = await request(app).post('/api/puestos').set(auth(admin)).send({ codigo: 'A-999', pabellon: 'B' });
    assert.equal(r.status, 400);
  });
});

describe('Épica 2 · Estiba formal con tarifa oficial', () => {
  test('las tarifas son públicas', async () => {
    const r = await request(app).get('/api/tarifas');
    assert.equal(r.status, 200);
    assert.ok(r.body.length >= 4);
  });

  test('el monto se calcula con la tarifa oficial (sin cupos)', async () => {
    const r = await request(app).post('/api/servicios-estiba').set(auth(comerciante))
      .send({ estibador_id: 1, comerciante_id: 2, tipo_carga: 'saco', cantidad: 40, monto: 999 });
    assert.equal(r.status, 201);
    assert.equal(r.body.monto, 80); // 40 sacos × S/ 2.00, ignora el monto enviado
  });

  test('no se puede registrar estiba con carnet suspendido', async () => {
    await request(app).patch('/api/estibadores/1/carnet').set(auth(admin)).send({ carnet_activo: false });
    const r = await request(app).post('/api/servicios-estiba').set(auth(admin))
      .send({ estibador_id: 1, comerciante_id: 1, tipo_carga: 'jaba', cantidad: 10 });
    assert.equal(r.status, 409);
  });

  test('DNI de estibador duplicado devuelve 409', async () => {
    const r = await request(app).post('/api/estibadores').set(auth(admin)).send({ dni: '45678912', nombre: 'Otro' });
    assert.equal(r.status, 409);
  });
});

describe('Épica 3 · Reservas de descarga y orden vehicular', () => {
  const base = { comerciante_id: 1, fecha: '2026-12-01', franja: '04:00-05:00', zona: 'Z1-Frutas' };

  test('reserva válida y normaliza la placa', async () => {
    const r = await request(app).post('/api/reservas').set(auth(comerciante)).send({ ...base, placa: 'abc-123' });
    assert.equal(r.status, 201);
    assert.equal(r.body.placa, 'ABC-123');
  });

  test('respeta la capacidad máxima por franja y zona', async () => {
    for (const placa of ['AAA-001', 'AAA-002', 'AAA-003']) {
      const ok = await request(app).post('/api/reservas').set(auth(admin)).send({ ...base, placa });
      assert.equal(ok.status, 201);
    }
    const llena = await request(app).post('/api/reservas').set(auth(admin)).send({ ...base, placa: 'AAA-004' });
    assert.equal(llena.status, 409);
  });

  test('registrar ingreso solo una vez', async () => {
    const r = await request(app).post('/api/reservas').set(auth(admin)).send({ ...base, placa: 'BBB-111' });
    const i1 = await request(app).patch(`/api/reservas/${r.body.id}/ingreso`).set(auth(admin));
    assert.equal(i1.status, 200);
    assert.equal(i1.body.estado, 'ingresado');
    const i2 = await request(app).patch(`/api/reservas/${r.body.id}/ingreso`).set(auth(admin));
    assert.equal(i2.status, 409);
  });

  test('placa con formato inválido es rechazada', async () => {
    const r = await request(app).post('/api/reservas').set(auth(admin)).send({ ...base, placa: 'XX' });
    assert.equal(r.status, 400);
  });
});

describe('Épica 4 · Salubridad', () => {
  test('inspector registra inspección conforme', async () => {
    const r = await request(app).post('/api/inspecciones').set(auth(inspector)).send({ puesto_id: 1, resultado: 'conforme' });
    assert.equal(r.status, 201);
  });

  test('inspección observada exige observaciones', async () => {
    const r = await request(app).post('/api/inspecciones').set(auth(inspector)).send({ puesto_id: 1, resultado: 'observado' });
    assert.equal(r.status, 400);
  });

  test('un comerciante no puede registrar inspecciones', async () => {
    const r = await request(app).post('/api/inspecciones').set(auth(comerciante)).send({ puesto_id: 1, resultado: 'conforme' });
    assert.equal(r.status, 403);
  });
});

describe('Épica 5 · Denuncias anónimas, indicadores y auditoría', () => {
  test('denuncia anónima sin sesión y seguimiento por código', async () => {
    const r = await request(app).post('/api/denuncias')
      .send({ tipo: 'cobro_cupos', descripcion: 'Me cobran S/ 5 por camión para descargar', ubicacion: 'Puerta 3' });
    assert.equal(r.status, 201);
    assert.match(r.body.codigo, /^DEN-[0-9A-F]{8}$/);
    const s = await request(app).get('/api/denuncias/seguimiento/' + r.body.codigo);
    assert.equal(s.status, 200);
    assert.equal(s.body.estado, 'recibida');
    assert.equal(s.body.descripcion, undefined, 'el seguimiento no expone el detalle');
  });

  test('intento de inyección SQL en el código de seguimiento es rechazado', async () => {
    const r = await request(app).get('/api/denuncias/seguimiento/' + encodeURIComponent("DEN-1' OR '1'='1"));
    assert.equal(r.status, 400);
  });

  test('solo admin ve y actualiza denuncias', async () => {
    await request(app).post('/api/denuncias').send({ tipo: 'extorsion', descripcion: 'Amenazas a comerciantes del pabellón B' });
    assert.equal((await request(app).get('/api/denuncias').set(auth(comerciante))).status, 403);
    const lista = await request(app).get('/api/denuncias').set(auth(admin));
    assert.equal(lista.status, 200);
    const upd = await request(app).patch(`/api/denuncias/${lista.body[0].id}`).set(auth(admin)).send({ estado: 'derivada_pnp' });
    assert.equal(upd.body.estado, 'derivada_pnp');
  });

  test('las acciones quedan en auditoría y los indicadores se actualizan', async () => {
    await request(app).post('/api/estibadores').set(auth(admin)).send({ dni: '40000001', nombre: 'Nuevo Estibador' });
    const aud = await request(app).get('/api/auditoria').set(auth(admin));
    assert.equal(aud.body[0].accion, 'crear');
    assert.equal(aud.body[0].entidad, 'estibador');
    const k = await request(app).get('/api/indicadores').set(auth(inspector));
    assert.equal(k.body.estibadores_con_carnet, 3);
    assert.equal(k.body.comerciantes_formalizados, 3);
  });
});
