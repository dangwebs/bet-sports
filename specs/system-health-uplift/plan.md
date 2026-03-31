# Plan: System Health Uplift

Resumen
-------
Mejorar la salud global del sistema: health checks, circuit breakers, backlog monitoring y alerting para evitar degradación silenciosa.

Objetivos
---------
- Exponer endpoints de `/_health` y `/_ready` con checks dependientes.
- Añadir monitorización de queue/backlog y circuit-breakers en componentes críticos.
