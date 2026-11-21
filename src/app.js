'use strict';

const path = require('node:path');
const express = require('express');
const helmet = require('helmet');
const api = require('./routes/api');

function crearApp() {
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);

  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'"],
          imgSrc: ["'self'", 'data:'],
          connectSrc: ["'self'"],
          objectSrc: ["'none'"],
          frameAncestors: ["'none'"],
        },
      },
    }),
  );
  app.use(express.json({ limit: '20kb' }));

  app.use('/api', api);
  app.use('/api', (_req, res) => res.status(404).json({ error: 'Ruta no encontrada' }));

  app.use(express.static(path.join(__dirname, '..', 'public'), { maxAge: '1h' }));

  // Manejador de errores: no expone detalles internos al cliente.
  app.use((err, _req, res, _next) => {
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON inválido' });
    if (err.type === 'entity.too.large') return res.status(413).json({ error: 'Solicitud demasiado grande' });
    if (process.env.NODE_ENV !== 'test') console.error(err);
    return res.status(500).json({ error: 'Error interno' });
  });

  return app;
}

module.exports = crearApp;
