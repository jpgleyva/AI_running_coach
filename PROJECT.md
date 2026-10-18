# AI Running Coach

Objetivo:
Crear un sistema multiagente para running y recomposición corporal.

Usuario:
- Corre 2-3 veces por semana
- Busca reducir grasa visceral
- Quiere abdominales visibles
- Tiene historial de molestias en rodilla derecha

Fuentes de datos:
- Garmin
- Amazfit/Zepp
- Google Calendar

Roadmap:
1. Agente simple: CLI conversacional de running y recomposición corporal,
   con el contexto del usuario y límites seguros para molestias de rodilla.
2. Tool Calling: herramientas locales para calcular ritmo medio y estimar
   tiempos de carrera.
3. MCP: servidor local para cálculos y conexión opcional a Zepp/Amazfit.
4. Memoria: perfil temporal confirmado y editable durante la sesión; no persistir
   los datos al cerrar.
5. Multiagente: coordinador automático con especialistas en running,
   nutrición/recomposición corporal y recuperación/seguridad de rodilla.
6. A2A