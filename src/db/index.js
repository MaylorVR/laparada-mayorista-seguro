'use strict';

const bcrypt = require('bcryptjs');
const config = require('../config');
const schema = require('./schema');

let pool = null;
let ready = null;

function createPool() {
  if (config.databaseUrl) {
    const { Pool } = require('pg');
    return new Pool({
      connectionString: config.databaseUrl,
      ssl: config.databaseUrl.includes('localhost') ? false : { rejectUnauthorized: true },
      max: 5,
    });
  }
  // Sin DATABASE_URL: PostgreSQL en memoria (desarrollo, pruebas y demo).
  const { newDb } = require('pg-mem');
  const mem = newDb({ autoCreateForeignKeyIndices: true });
  const { Pool } = mem.adapters.createPg();
  return new Pool();
}

const TARIFAS = [
  ['saco', 'Saco de papa o tubérculo (hasta 50 kg)', 2.0],
  ['jaba', 'Jaba de fruta', 1.5],
  ['caja', 'Caja de verdura u hortaliza', 1.0],
  ['bulto', 'Bulto grande (más de 50 kg)', 3.5],
];

async function seed(db) {
  const { rows } = await db.query('SELECT COUNT(*) AS n FROM usuarios');
  if (Number(rows[0].n) > 0) return;

  const hash = await bcrypt.hash(config.demoPassword, 10);
  const usuarios = [
    ['admin@mayorista.pe', 'Administración del Mercado', 'admin'],
    ['inspector@mayorista.pe', 'Inspector Sanitario', 'inspector'],
    ['comerciante@mayorista.pe', 'Comerciante Demo', 'comerciante'],
  ];
  for (const [email, nombre, rol] of usuarios) {
    await db.query(
      'INSERT INTO usuarios (email, nombre, rol, password_hash) VALUES ($1, $2, $3, $4)',
      [email, nombre, rol, hash],
    );
  }
  for (const [tipo, desc, precio] of TARIFAS) {
    await db.query(
      'INSERT INTO tarifas_estiba (tipo_carga, descripcion, precio_unitario) VALUES ($1, $2, $3)',
      [tipo, desc, precio],
    );
  }
  const comerciantes = [
    ['20512345678', 'Frutas del Valle SAC', 'frutas', '987654321'],
    ['10456789012', 'Papas Huancayo EIRL', 'tuberculos', '912345678'],
    ['20678901234', 'Verduras Frescas Lima SAC', 'verduras', '934567890'],
  ];
  for (const c of comerciantes) {
    await db.query(
      'INSERT INTO comerciantes (ruc, razon_social, rubro, telefono) VALUES ($1, $2, $3, $4)',
      c,
    );
  }
  const puestos = [['A-101', 'A', 1], ['B-205', 'B', 2], ['C-310', 'C', 3], ['A-102', 'A', null]];
  for (const p of puestos) {
    await db.query('INSERT INTO puestos (codigo, pabellon, comerciante_id) VALUES ($1, $2, $3)', p);
  }
  const estibadores = [['45678912', 'Juan Quispe Mamani'], ['47891234', 'Rosa Huamán Torres']];
  for (const e of estibadores) {
    await db.query('INSERT INTO estibadores (dni, nombre) VALUES ($1, $2)', e);
  }
}

async function init() {
  if (!pool) pool = createPool();
  if (!ready) {
    ready = (async () => {
      await pool.query(schema);
      await seed(pool);
    })().catch((err) => {
      ready = null;
      throw err;
    });
  }
  await ready;
  return pool;
}

async function query(text, params) {
  const db = await init();
  return db.query(text, params);
}

// Solo para pruebas: reinicia la base en memoria.
async function reset() {
  if (pool && typeof pool.end === 'function') {
    try { await pool.end(); } catch { /* pg-mem puede no soportar end() */ }
  }
  pool = null;
  ready = null;
  await init();
}

module.exports = { init, query, reset, TARIFAS };
