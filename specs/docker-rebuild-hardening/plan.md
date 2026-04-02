# Plan: Hardening del Rebuild Docker

Fecha: 2026-04-02

## Enfoque

Atacar primero los errores TypeScript que bloquean `Dockerfile.portable`, luego estabilizar `labeler` en `docker-compose.dev.yml` y finalmente persistir la configuracion de rebuild en un artefacto mantenible del repositorio.

## Pasos

1. Corregir tipados y props en los archivos del frontend que rompen `npm run build`.
2. Ajustar el comando del servicio `labeler` para usar un wrapper seguro y existente en la imagen.
3. Guardar la forma canonica de reconstruccion en el repo.
4. Validar con diagnosticos y verificaciones ligeras orientadas al build.

## Resultado esperado

- Rebuild Docker portable alineado con el codigo actual.
- Frontend sin errores TS bloqueantes para la imagen.
- `labeler` configurado de forma estable en Compose.
