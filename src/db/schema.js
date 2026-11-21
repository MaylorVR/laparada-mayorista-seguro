'use strict';

// Esquema de la base de datos (PostgreSQL). Se aplica al iniciar de forma idempotente.
module.exports = `
CREATE TABLE IF NOT EXISTS usuarios (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  nombre TEXT NOT NULL,
  rol TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comerciantes (
  id SERIAL PRIMARY KEY,
  ruc TEXT NOT NULL UNIQUE,
  razon_social TEXT NOT NULL,
  rubro TEXT NOT NULL,
  telefono TEXT,
  estado TEXT NOT NULL DEFAULT 'formalizado',
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS puestos (
  id SERIAL PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  pabellon TEXT NOT NULL,
  comerciante_id INTEGER REFERENCES comerciantes(id),
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS estibadores (
  id SERIAL PRIMARY KEY,
  dni TEXT NOT NULL UNIQUE,
  nombre TEXT NOT NULL,
  carnet_activo BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tarifas_estiba (
  tipo_carga TEXT PRIMARY KEY,
  descripcion TEXT NOT NULL,
  precio_unitario NUMERIC(8,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS servicios_estiba (
  id SERIAL PRIMARY KEY,
  estibador_id INTEGER NOT NULL REFERENCES estibadores(id),
  comerciante_id INTEGER NOT NULL REFERENCES comerciantes(id),
  tipo_carga TEXT NOT NULL REFERENCES tarifas_estiba(tipo_carga),
  cantidad INTEGER NOT NULL,
  monto NUMERIC(10,2) NOT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reservas_descarga (
  id SERIAL PRIMARY KEY,
  placa TEXT NOT NULL,
  comerciante_id INTEGER NOT NULL REFERENCES comerciantes(id),
  fecha TEXT NOT NULL,
  franja TEXT NOT NULL,
  zona TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'reservada',
  ingreso_en TIMESTAMP,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inspecciones (
  id SERIAL PRIMARY KEY,
  puesto_id INTEGER NOT NULL REFERENCES puestos(id),
  inspector_id INTEGER NOT NULL REFERENCES usuarios(id),
  resultado TEXT NOT NULL,
  observaciones TEXT,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS denuncias (
  id SERIAL PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  tipo TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  ubicacion TEXT,
  estado TEXT NOT NULL DEFAULT 'recibida',
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auditoria (
  id SERIAL PRIMARY KEY,
  usuario_id INTEGER,
  accion TEXT NOT NULL,
  entidad TEXT NOT NULL,
  entidad_id INTEGER,
  creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);
`;
