'use strict';

const { z } = require('zod');

const texto = (max) => z.string().trim().min(1).max(max);

const schemas = {
  login: z.object({
    email: z.string().trim().toLowerCase().email().max(120),
    password: z.string().min(1).max(200),
  }),

  comerciante: z.object({
    ruc: z.string().regex(/^(10|20)\d{9}$/, 'RUC debe tener 11 dígitos y empezar con 10 o 20'),
    razon_social: texto(150),
    rubro: z.enum(['frutas', 'verduras', 'tuberculos', 'abarrotes']),
    telefono: z.string().regex(/^9\d{8}$/, 'Teléfono celular de 9 dígitos').optional(),
  }),

  puesto: z.object({
    codigo: z.string().regex(/^[A-Z]-\d{3}$/, 'Código con formato A-101'),
    pabellon: z.string().regex(/^[A-Z]$/),
    comerciante_id: z.number().int().positive().nullable().optional(),
  }),

  asignarPuesto: z.object({
    comerciante_id: z.number().int().positive(),
  }),

  estibador: z.object({
    dni: z.string().regex(/^\d{8}$/, 'DNI de 8 dígitos'),
    nombre: texto(120),
  }),

  servicioEstiba: z.object({
    estibador_id: z.number().int().positive(),
    comerciante_id: z.number().int().positive(),
    tipo_carga: z.enum(['saco', 'jaba', 'caja', 'bulto']),
    cantidad: z.number().int().positive().max(5000),
  }),

  reserva: z.object({
    placa: z.string().trim().toUpperCase().regex(/^[A-Z0-9]{3}-\d{3}$/, 'Placa con formato ABC-123'),
    comerciante_id: z.number().int().positive(),
    fecha: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Fecha AAAA-MM-DD'),
    franja: z.enum(['02:00-03:00', '03:00-04:00', '04:00-05:00', '05:00-06:00', '06:00-07:00']),
    zona: z.enum(['Z1-Frutas', 'Z2-Verduras', 'Z3-Tuberculos']),
  }),

  inspeccion: z.object({
    puesto_id: z.number().int().positive(),
    resultado: z.enum(['conforme', 'observado', 'clausurado']),
    observaciones: z.string().trim().max(500).optional(),
  }),

  denuncia: z.object({
    tipo: z.enum(['cobro_cupos', 'extorsion', 'insalubridad', 'caos_vehicular', 'otro']),
    descripcion: z.string().trim().min(10).max(1000),
    ubicacion: z.string().trim().max(150).optional(),
  }),

  fechaFiltro: z.iso.date(),

  estadoDenuncia: z.object({
    estado: z.enum(['recibida', 'en_investigacion', 'derivada_pnp', 'cerrada']),
  }),
};

function validar(schema) {
  return (req, res, next) => {
    const r = schema.safeParse(req.body ?? {});
    if (!r.success) {
      return res.status(400).json({
        error: 'Datos inválidos',
        detalles: r.error.issues.map((i) => ({ campo: i.path.join('.'), mensaje: i.message })),
      });
    }
    req.body = r.data;
    return next();
  };
}

module.exports = { schemas, validar };
