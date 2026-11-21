'use strict';

const crypto = require('node:crypto');
const express = require('express');
const bcrypt = require('bcryptjs');
const rateLimit = require('express-rate-limit');
const db = require('../db');
const config = require('../config');
const { firmarToken, autenticar, autorizar } = require('../middleware/auth');
const { schemas, validar } = require('../validation');

const router = express.Router();

const limiteLogin = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 10,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  skip: () => process.env.NODE_ENV === 'test',
  message: { error: 'Demasiados intentos, espere 15 minutos' },
});

const limiteDenuncias = rateLimit({
  windowMs: 60 * 60 * 1000,
  limit: 20,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  skip: () => process.env.NODE_ENV === 'test',
  message: { error: 'Demasiadas denuncias desde esta conexión' },
});

async function auditar(req, accion, entidad, entidadId) {
  await db.query(
    'INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id) VALUES ($1, $2, $3, $4)',
    [req.usuario ? req.usuario.id : null, accion, entidad, entidadId ?? null],
  );
}

function idParam(req, res) {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ error: 'Identificador inválido' });
    return null;
  }
  return id;
}

async function existe(tabla, id) {
  // tabla siempre viene de una lista fija del código, nunca del usuario
  const permitidas = ['comerciantes', 'estibadores', 'puestos'];
  if (!permitidas.includes(tabla)) throw new Error('tabla no permitida');
  const { rows } = await db.query(`SELECT id FROM ${tabla} WHERE id = $1`, [id]);
  return rows.length > 0;
}

// ---------- Salud ----------
router.get('/salud', async (_req, res) => {
  await db.query('SELECT 1 AS ok');
  res.json({ estado: 'ok', version: process.env.APP_VERSION || 'local' });
});

// ---------- Autenticación ----------
router.post('/auth/login', limiteLogin, validar(schemas.login), async (req, res) => {
  const { email, password } = req.body;
  const { rows } = await db.query('SELECT * FROM usuarios WHERE email = $1', [email]);
  const usuario = rows[0];
  const ok = usuario ? await bcrypt.compare(password, usuario.password_hash) : false;
  if (!ok) return res.status(401).json({ error: 'Credenciales incorrectas' });
  return res.json({
    token: firmarToken(usuario),
    usuario: { id: usuario.id, nombre: usuario.nombre, rol: usuario.rol, email: usuario.email },
  });
});

router.get('/auth/yo', autenticar, (req, res) => res.json({ usuario: req.usuario }));

// ---------- Transparencia (público) ----------
router.get('/tarifas', async (_req, res) => {
  const { rows } = await db.query('SELECT * FROM tarifas_estiba ORDER BY precio_unitario');
  res.json(rows.map((t) => ({ ...t, precio_unitario: Number(t.precio_unitario) })));
});

// ---------- Denuncias anónimas (público) ----------
router.post('/denuncias', limiteDenuncias, validar(schemas.denuncia), async (req, res) => {
  const codigo = 'DEN-' + crypto.randomBytes(4).toString('hex').toUpperCase();
  const { tipo, descripcion, ubicacion } = req.body;
  const { rows } = await db.query(
    'INSERT INTO denuncias (codigo, tipo, descripcion, ubicacion) VALUES ($1, $2, $3, $4) RETURNING id, codigo, estado',
    [codigo, tipo, descripcion, ubicacion ?? null],
  );
  res.status(201).json(rows[0]);
});

router.get('/denuncias/seguimiento/:codigo', async (req, res) => {
  const codigo = String(req.params.codigo).toUpperCase();
  if (!/^DEN-[0-9A-F]{8}$/.test(codigo)) return res.status(400).json({ error: 'Código inválido' });
  const { rows } = await db.query('SELECT codigo, tipo, estado, creado_en FROM denuncias WHERE codigo = $1', [codigo]);
  if (!rows.length) return res.status(404).json({ error: 'Denuncia no encontrada' });
  return res.json(rows[0]);
});

// ---------- Todo lo de abajo requiere sesión ----------
router.use(autenticar);

router.get('/denuncias', autorizar('admin'), async (_req, res) => {
  const { rows } = await db.query('SELECT * FROM denuncias ORDER BY id DESC');
  res.json(rows);
});

router.patch('/denuncias/:id', autorizar('admin'), validar(schemas.estadoDenuncia), async (req, res) => {
  const id = idParam(req, res);
  if (!id) return undefined;
  const { rows } = await db.query('UPDATE denuncias SET estado = $1 WHERE id = $2 RETURNING *', [req.body.estado, id]);
  if (!rows.length) return res.status(404).json({ error: 'Denuncia no encontrada' });
  await auditar(req, 'actualizar_estado', 'denuncia', id);
  return res.json(rows[0]);
});

// ---------- Comerciantes (padrón) ----------
router.get('/comerciantes', async (_req, res) => {
  const { rows } = await db.query('SELECT * FROM comerciantes ORDER BY id');
  res.json(rows);
});

router.post('/comerciantes', autorizar('admin'), validar(schemas.comerciante), async (req, res) => {
  const { ruc, razon_social, rubro, telefono } = req.body;
  const dup = await db.query('SELECT id FROM comerciantes WHERE ruc = $1', [ruc]);
  if (dup.rows.length) return res.status(409).json({ error: 'El RUC ya está registrado' });
  const { rows } = await db.query(
    'INSERT INTO comerciantes (ruc, razon_social, rubro, telefono) VALUES ($1, $2, $3, $4) RETURNING *',
    [ruc, razon_social, rubro, telefono ?? null],
  );
  await auditar(req, 'crear', 'comerciante', rows[0].id);
  return res.status(201).json(rows[0]);
});

// ---------- Puestos ----------
router.get('/puestos', async (_req, res) => {
  const { rows } = await db.query(
    `SELECT p.id, p.codigo, p.pabellon, p.comerciante_id, c.razon_social
       FROM puestos p LEFT JOIN comerciantes c ON c.id = p.comerciante_id
      ORDER BY p.codigo`,
  );
  res.json(rows);
});

router.post('/puestos', autorizar('admin'), validar(schemas.puesto), async (req, res) => {
  const { codigo, pabellon, comerciante_id } = req.body;
  if (codigo[0] !== pabellon) return res.status(400).json({ error: 'El código debe empezar con la letra del pabellón' });
  const dup = await db.query('SELECT id FROM puestos WHERE codigo = $1', [codigo]);
  if (dup.rows.length) return res.status(409).json({ error: 'El puesto ya existe' });
  if (comerciante_id && !(await existe('comerciantes', comerciante_id))) {
    return res.status(404).json({ error: 'Comerciante no encontrado' });
  }
  const { rows } = await db.query(
    'INSERT INTO puestos (codigo, pabellon, comerciante_id) VALUES ($1, $2, $3) RETURNING *',
    [codigo, pabellon, comerciante_id ?? null],
  );
  await auditar(req, 'crear', 'puesto', rows[0].id);
  return res.status(201).json(rows[0]);
});

router.patch('/puestos/:id/asignar', autorizar('admin'), validar(schemas.asignarPuesto), async (req, res) => {
  const id = idParam(req, res);
  if (!id) return undefined;
  if (!(await existe('comerciantes', req.body.comerciante_id))) {
    return res.status(404).json({ error: 'Comerciante no encontrado' });
  }
  const { rows } = await db.query('SELECT * FROM puestos WHERE id = $1', [id]);
  if (!rows.length) return res.status(404).json({ error: 'Puesto no encontrado' });
  if (rows[0].comerciante_id) return res.status(409).json({ error: 'El puesto ya está asignado' });
  const upd = await db.query('UPDATE puestos SET comerciante_id = $1 WHERE id = $2 RETURNING *', [req.body.comerciante_id, id]);
  await auditar(req, 'asignar', 'puesto', id);
  return res.json(upd.rows[0]);
});

// ---------- Estiba formal ----------
router.get('/estibadores', async (_req, res) => {
  const { rows } = await db.query('SELECT * FROM estibadores ORDER BY id');
  res.json(rows);
});

router.post('/estibadores', autorizar('admin'), validar(schemas.estibador), async (req, res) => {
  const dup = await db.query('SELECT id FROM estibadores WHERE dni = $1', [req.body.dni]);
  if (dup.rows.length) return res.status(409).json({ error: 'El DNI ya está registrado' });
  const { rows } = await db.query(
    'INSERT INTO estibadores (dni, nombre) VALUES ($1, $2) RETURNING *',
    [req.body.dni, req.body.nombre],
  );
  await auditar(req, 'crear', 'estibador', rows[0].id);
  return res.status(201).json(rows[0]);
});

router.patch('/estibadores/:id/carnet', autorizar('admin'), async (req, res) => {
  const id = idParam(req, res);
  if (!id) return undefined;
  const activo = req.body && req.body.carnet_activo === true;
  const { rows } = await db.query('UPDATE estibadores SET carnet_activo = $1 WHERE id = $2 RETURNING *', [activo, id]);
  if (!rows.length) return res.status(404).json({ error: 'Estibador no encontrado' });
  await auditar(req, activo ? 'activar_carnet' : 'suspender_carnet', 'estibador', id);
  return res.json(rows[0]);
});

router.get('/servicios-estiba', async (_req, res) => {
  const { rows } = await db.query(
    `SELECT s.*, e.nombre AS estibador, c.razon_social AS comerciante
       FROM servicios_estiba s
       JOIN estibadores e ON e.id = s.estibador_id
       JOIN comerciantes c ON c.id = s.comerciante_id
      ORDER BY s.id DESC`,
  );
  res.json(rows.map((s) => ({ ...s, monto: Number(s.monto) })));
});

router.post('/servicios-estiba', autorizar('admin', 'comerciante'), validar(schemas.servicioEstiba), async (req, res) => {
  const { estibador_id, comerciante_id, tipo_carga, cantidad } = req.body;
  const est = await db.query('SELECT carnet_activo FROM estibadores WHERE id = $1', [estibador_id]);
  if (!est.rows.length) return res.status(404).json({ error: 'Estibador no encontrado' });
  if (!est.rows[0].carnet_activo) return res.status(409).json({ error: 'El estibador no tiene carnet activo' });
  if (!(await existe('comerciantes', comerciante_id))) return res.status(404).json({ error: 'Comerciante no encontrado' });
  const tarifa = await db.query('SELECT precio_unitario FROM tarifas_estiba WHERE tipo_carga = $1', [tipo_carga]);
  // El monto lo calcula el sistema con la tarifa oficial: nadie puede cobrar "cupos" adicionales.
  const monto = Math.round(Number(tarifa.rows[0].precio_unitario) * cantidad * 100) / 100;
  const { rows } = await db.query(
    'INSERT INTO servicios_estiba (estibador_id, comerciante_id, tipo_carga, cantidad, monto) VALUES ($1, $2, $3, $4, $5) RETURNING *',
    [estibador_id, comerciante_id, tipo_carga, cantidad, monto],
  );
  await auditar(req, 'registrar', 'servicio_estiba', rows[0].id);
  return res.status(201).json({ ...rows[0], monto });
});

// ---------- Reservas de descarga (orden vehicular) ----------
router.get('/reservas', async (req, res) => {
  const filtro = schemas.fechaFiltro.safeParse(req.query.fecha);
  const fecha = filtro.success ? filtro.data : null;
  const { rows } = fecha
    ? await db.query('SELECT * FROM reservas_descarga WHERE fecha = $1 ORDER BY franja, id', [fecha])
    : await db.query('SELECT * FROM reservas_descarga ORDER BY fecha DESC, franja, id');
  res.json(rows);
});

router.post('/reservas', autorizar('admin', 'comerciante'), validar(schemas.reserva), async (req, res) => {
  const { placa, comerciante_id, fecha, franja, zona } = req.body;
  if (!(await existe('comerciantes', comerciante_id))) return res.status(404).json({ error: 'Comerciante no encontrado' });
  const ocupadas = await db.query(
    "SELECT COUNT(*) AS n FROM reservas_descarga WHERE fecha = $1 AND franja = $2 AND zona = $3 AND estado <> 'cancelada'",
    [fecha, franja, zona],
  );
  if (Number(ocupadas.rows[0].n) >= config.capacidadPorFranja) {
    return res.status(409).json({ error: 'Franja llena para esa zona, elija otra hora' });
  }
  const misma = await db.query(
    "SELECT id FROM reservas_descarga WHERE fecha = $1 AND franja = $2 AND placa = $3 AND estado <> 'cancelada'",
    [fecha, franja, placa],
  );
  if (misma.rows.length) return res.status(409).json({ error: 'Ese vehículo ya tiene reserva en esa franja' });
  const { rows } = await db.query(
    'INSERT INTO reservas_descarga (placa, comerciante_id, fecha, franja, zona) VALUES ($1, $2, $3, $4, $5) RETURNING *',
    [placa, comerciante_id, fecha, franja, zona],
  );
  await auditar(req, 'crear', 'reserva', rows[0].id);
  return res.status(201).json(rows[0]);
});

router.patch('/reservas/:id/ingreso', autorizar('admin'), async (req, res) => {
  const id = idParam(req, res);
  if (!id) return undefined;
  const actual = await db.query('SELECT estado FROM reservas_descarga WHERE id = $1', [id]);
  if (!actual.rows.length) return res.status(404).json({ error: 'Reserva no encontrada' });
  if (actual.rows[0].estado !== 'reservada') return res.status(409).json({ error: 'La reserva no está pendiente' });
  const { rows } = await db.query(
    "UPDATE reservas_descarga SET estado = 'ingresado', ingreso_en = NOW() WHERE id = $1 RETURNING *",
    [id],
  );
  await auditar(req, 'registrar_ingreso', 'reserva', id);
  return res.json(rows[0]);
});

// ---------- Inspecciones sanitarias ----------
router.get('/inspecciones', async (_req, res) => {
  const { rows } = await db.query(
    `SELECT i.*, p.codigo AS puesto, u.nombre AS inspector
       FROM inspecciones i
       JOIN puestos p ON p.id = i.puesto_id
       JOIN usuarios u ON u.id = i.inspector_id
      ORDER BY i.id DESC`,
  );
  res.json(rows);
});

router.post('/inspecciones', autorizar('inspector', 'admin'), validar(schemas.inspeccion), async (req, res) => {
  const { puesto_id, resultado, observaciones } = req.body;
  if (!(await existe('puestos', puesto_id))) return res.status(404).json({ error: 'Puesto no encontrado' });
  if (resultado !== 'conforme' && !observaciones) {
    return res.status(400).json({ error: 'Las observaciones son obligatorias si el resultado no es conforme' });
  }
  const { rows } = await db.query(
    'INSERT INTO inspecciones (puesto_id, inspector_id, resultado, observaciones) VALUES ($1, $2, $3, $4) RETURNING *',
    [puesto_id, req.usuario.id, resultado, observaciones ?? null],
  );
  await auditar(req, 'crear', 'inspeccion', rows[0].id);
  return res.status(201).json(rows[0]);
});

// ---------- Indicadores y auditoría ----------
router.get('/indicadores', async (_req, res) => {
  const contar = async (sql) => Number((await db.query(sql)).rows[0].n);
  res.json({
    comerciantes_formalizados: await contar('SELECT COUNT(*) AS n FROM comerciantes'),
    puestos_asignados: await contar('SELECT COUNT(*) AS n FROM puestos WHERE comerciante_id IS NOT NULL'),
    estibadores_con_carnet: await contar('SELECT COUNT(*) AS n FROM estibadores WHERE carnet_activo = TRUE'),
    servicios_estiba: await contar('SELECT COUNT(*) AS n FROM servicios_estiba'),
    reservas_descarga: await contar('SELECT COUNT(*) AS n FROM reservas_descarga'),
    inspecciones_observadas: await contar("SELECT COUNT(*) AS n FROM inspecciones WHERE resultado <> 'conforme'"),
    denuncias_abiertas: await contar("SELECT COUNT(*) AS n FROM denuncias WHERE estado <> 'cerrada'"),
  });
});

router.get('/auditoria', autorizar('admin'), async (_req, res) => {
  const { rows } = await db.query('SELECT * FROM auditoria ORDER BY id DESC LIMIT 100');
  res.json(rows);
});

module.exports = router;
