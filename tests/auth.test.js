'use strict';

const { test, describe, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { app, db, request, login, PASS } = require('./helpers');

describe('Autenticación y autorización', () => {
  beforeEach(() => db.reset());

  test('login correcto devuelve token y rol', async () => {
    const r = await request(app).post('/api/auth/login').send({ email: 'admin@mayorista.pe', password: PASS });
    assert.equal(r.status, 200);
    assert.ok(r.body.token);
    assert.equal(r.body.usuario.rol, 'admin');
    assert.equal(r.body.usuario.password_hash, undefined, 'nunca debe exponer el hash');
  });

  test('contraseña incorrecta devuelve 401 sin revelar si el usuario existe', async () => {
    const a = await request(app).post('/api/auth/login').send({ email: 'admin@mayorista.pe', password: 'mala' });
    const b = await request(app).post('/api/auth/login').send({ email: 'nadie@mayorista.pe', password: 'mala' });
    assert.equal(a.status, 401);
    assert.equal(b.status, 401);
    assert.deepEqual(a.body, b.body);
  });

  test('login con datos inválidos devuelve 400', async () => {
    const r = await request(app).post('/api/auth/login').send({ email: 'no-es-correo' });
    assert.equal(r.status, 400);
  });

  test('rutas privadas exigen token', async () => {
    const r = await request(app).get('/api/comerciantes');
    assert.equal(r.status, 401);
  });

  test('token manipulado es rechazado', async () => {
    const token = await login('comerciante@mayorista.pe');
    const [h, p, s] = token.split('.');
    const payload = JSON.parse(Buffer.from(p, 'base64url').toString());
    payload.rol = 'admin';
    const falso = [h, Buffer.from(JSON.stringify(payload)).toString('base64url'), s].join('.');
    const r = await request(app).get('/api/auditoria').set('Authorization', 'Bearer ' + falso);
    assert.equal(r.status, 401);
  });

  test('un comerciante no puede ver la auditoría (403)', async () => {
    const token = await login('comerciante@mayorista.pe');
    const r = await request(app).get('/api/auditoria').set('Authorization', 'Bearer ' + token);
    assert.equal(r.status, 403);
  });

  test('/api/auth/yo devuelve el usuario de la sesión', async () => {
    const token = await login('inspector@mayorista.pe');
    const r = await request(app).get('/api/auth/yo').set('Authorization', 'Bearer ' + token);
    assert.equal(r.status, 200);
    assert.equal(r.body.usuario.rol, 'inspector');
  });
});

describe('Cabeceras de seguridad y errores', () => {
  test('helmet añade CSP y oculta x-powered-by', async () => {
    const r = await request(app).get('/api/salud');
    assert.equal(r.status, 200);
    assert.ok(r.headers['content-security-policy']);
    assert.equal(r.headers['x-powered-by'], undefined);
  });

  test('JSON mal formado devuelve 400', async () => {
    const r = await request(app).post('/api/auth/login').set('Content-Type', 'application/json').send('{"email":');
    assert.equal(r.status, 400);
  });

  test('ruta inexistente: 401 sin sesión (no revela rutas) y 404 con sesión', async () => {
    assert.equal((await request(app).get('/api/no-existe')).status, 401);
    const token = await login('admin@mayorista.pe');
    const r = await request(app).get('/api/no-existe').set('Authorization', 'Bearer ' + token);
    assert.equal(r.status, 404);
  });
});
