# Mayorista Seguro

Sistema web para ordenar el traslado del comercio mayorista de **La Parada** al **Mercado Mayorista de Santa Anita** (Lima). Ataca los cuatro problemas del caso:

| Problema en La Parada | Módulo del sistema |
|---|---|
| Comercio sin registro | Padrón de comerciantes formalizados (RUC) y asignación de puestos |
| Control de la estiba por grupos que cobran cupos | Estibadores con carnet, **tarifa oficial pública** y monto calculado por el sistema |
| Caos vehicular | Reservas de franjas de descarga con capacidad máxima por zona y registro de ingreso |
| Falta de salubridad | Inspecciones sanitarias por puesto (conforme / observado / clausurado) |
| Miedo a denunciar | Denuncias **anónimas** con código de seguimiento |

Además: autenticación JWT con roles (admin, inspector, comerciante), auditoría de todas las acciones e indicadores.

## Arquitectura

```
Navegador (HTML + JS sin frameworks, CSP estricta)
        │  HTTPS / JSON
        ▼
Vercel ── función serverless Node.js 22 ── Express 5
              │  helmet · rate limit · zod · JWT/bcrypt · roles
              ▼
        PostgreSQL (Neon) — o PostgreSQL en memoria (pg-mem) si no hay DATABASE_URL
```

- `public/` frontend estático.
- `src/app.js` app Express (seguridad transversal), `src/routes/api.js` endpoints, `src/db/` esquema y datos semilla.
- `api/index.js` punto de entrada serverless para Vercel.
- `tests/` 31 pruebas de integración (node:test + supertest), una suite por épica.

## Estrategia de ramas

- `main` → producción (Vercel production). Solo recibe cambios por **Pull Request** desde `test` con el pipeline en verde.
- `test` → rama de pruebas/integración (despliega un *preview* en Vercel).
- `feature/*` → trabajo de cada historia; se integra en `test`.

## Pipeline CI/CD (`.github/workflows/ci-cd.yml`)

1. **Build y lint**: `npm ci`, ESLint (`no-eval`, `no-implied-eval`), verificación de build.
2. **Pruebas**: 31 pruebas con cobertura; reporte JUnit como artefacto y resumen en el job.
3. **Seguridad**: npm audit (SCA), Gitleaks (secretos en todo el historial), Semgrep (SAST) y, en PRs, *dependency review*. CodeQL corre en `codeql.yml`.
4. **Deploy**: `main` → producción en Vercel con prueba de humo; `test` → preview.

## Ejecutar en local

```bash
npm install
npm start          # http://localhost:3000
npm test           # pruebas
npm run lint
```

Variables de entorno: `JWT_SECRET` (obligatoria en producción, ≥ 32 caracteres), `DATABASE_URL` (opcional), `DEMO_PASSWORD` (contraseña de las cuentas de demostración).

Cuentas de demostración: `admin@mayorista.pe`, `inspector@mayorista.pe`, `comerciante@mayorista.pe`.
