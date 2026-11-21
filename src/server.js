'use strict';

const config = require('./config');
const db = require('./db');
const crearApp = require('./app');

const app = crearApp();

db.init()
  .then(() => {
    app.listen(config.port, () => {
      console.log(`Mayorista Seguro escuchando en http://localhost:${config.port}`);
    });
  })
  .catch((err) => {
    console.error('No se pudo iniciar la base de datos', err);
    process.exit(1);
  });
