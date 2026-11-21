'use strict';

const isProduction = process.env.NODE_ENV === 'production';

function jwtSecret() {
  const secret = process.env.JWT_SECRET;
  if (secret && secret.length >= 32) return secret;
  if (isProduction) {
    throw new Error('JWT_SECRET debe estar definido (mínimo 32 caracteres) en producción');
  }
  return 'solo-desarrollo-no-usar-en-produccion-0000';
}

module.exports = {
  isProduction,
  port: Number(process.env.PORT) || 3000,
  databaseUrl: process.env.DATABASE_URL || '',
  jwtSecret,
  jwtExpiresIn: '8h',
  // Capacidad máxima de camiones por franja horaria y zona de descarga
  capacidadPorFranja: Number(process.env.CAPACIDAD_FRANJA) || 3,
  demoPassword: process.env.DEMO_PASSWORD || 'Demo2026!',
};
