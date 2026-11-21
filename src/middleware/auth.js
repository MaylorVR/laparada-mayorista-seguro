'use strict';

const jwt = require('jsonwebtoken');
const config = require('../config');

function firmarToken(usuario) {
  return jwt.sign(
    { sub: usuario.id, rol: usuario.rol, nombre: usuario.nombre },
    config.jwtSecret(),
    { expiresIn: config.jwtExpiresIn, algorithm: 'HS256' },
  );
}

function autenticar(req, res, next) {
  const header = req.get('authorization') || '';
  const [tipo, token] = header.split(' ');
  if (tipo !== 'Bearer' || !token) {
    return res.status(401).json({ error: 'Se requiere iniciar sesión' });
  }
  try {
    const payload = jwt.verify(token, config.jwtSecret(), { algorithms: ['HS256'] });
    req.usuario = { id: payload.sub, rol: payload.rol, nombre: payload.nombre };
    return next();
  } catch {
    return res.status(401).json({ error: 'Sesión inválida o vencida' });
  }
}

function autorizar(...roles) {
  return (req, res, next) => {
    if (!req.usuario || !roles.includes(req.usuario.rol)) {
      return res.status(403).json({ error: 'No tiene permiso para esta acción' });
    }
    return next();
  };
}

module.exports = { firmarToken, autenticar, autorizar };
