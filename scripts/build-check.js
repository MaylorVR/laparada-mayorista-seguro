'use strict';

// "Build" de la app: verifica que todos los módulos cargan y que los archivos
// estáticos existen. Falla el pipeline si falta algo antes de desplegar.
const fs = require('node:fs');
const path = require('node:path');

const raiz = path.join(__dirname, '..');
const requeridos = ['public/index.html', 'public/app.js', 'public/styles.css', 'api/index.js'];
for (const f of requeridos) {
  if (!fs.existsSync(path.join(raiz, f))) {
    console.error('Falta el archivo ' + f);
    process.exit(1);
  }
}
process.env.NODE_ENV = process.env.NODE_ENV || 'test';
require('../src/app');
require('../src/db');
console.log('Build OK: módulos cargan y estáticos presentes (' + requeridos.length + ' archivos)');
