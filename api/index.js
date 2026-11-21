'use strict';

// Punto de entrada para Vercel (función serverless que envuelve la app Express).
const crearApp = require('../src/app');

module.exports = crearApp();
