'use strict';

process.env.NODE_ENV = 'test';
delete process.env.DATABASE_URL;

const request = require('supertest');
const db = require('../src/db');
const crearApp = require('../src/aplicacion');

const app = crearApp();
const PASS = 'Demo2026!';

async function login(email) {
  const r = await request(app).post('/api/auth/login').send({ email, password: PASS });
  if (r.status !== 200) throw new Error('login falló para ' + email);
  return r.body.token;
}

module.exports = { app, db, request, login, PASS };
