# AI Running Coach

Agente conversacional para running y recomposición corporal, conectado a GitHub
Copilot mediante el SDK oficial de Python. Expone cálculos locales mediante MCP
y permite conectar opcionalmente el servidor MCP Zepp/Amazfit.

## Requisitos

- Python 3.11 o posterior.
- Una cuenta de GitHub Copilot con uso disponible. El plan gratuito puede tener
  límites de uso.
- Acceso a internet para que el SDK descargue su runtime la primera vez.

## Instalación en Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Instala y autentica GitHub Copilot CLI siguiendo la
[guía oficial](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).
El SDK usa la autenticación guardada por esa CLI. Si aún no has iniciado sesión,
abre `copilot`, completa el inicio de sesión y sal de esa sesión. Luego inicia el
coach:

```powershell
copilot
```

Tras completar el inicio de sesión y salir de Copilot CLI:

```powershell
running-coach
```

El coach inicia automáticamente su servidor MCP local cuando crea la sesión.

## Conexión opcional a Zepp/Amazfit

El agente puede lanzar como proceso separado el servidor
[zepp-mcp](https://github.com/DhavalBhimani44/zepp-mcp). No se copia ni se instala
en el entorno del coach: se ejecuta desde su propio checkout y lockfile, porque
usa una versión distinta del SDK MCP. Necesitas tener [uv](https://docs.astral.sh/uv/)
instalado.

En PowerShell:

```powershell
$zeppPath = "$env:LOCALAPPDATA\zepp-mcp"
git clone https://github.com/DhavalBhimani44/zepp-mcp.git $zeppPath
git -C $zeppPath checkout 9ba4f58ec19c300a74751386fc9a8d22aebbbfff
uv sync --locked --directory $zeppPath
Copy-Item "$zeppPath\.env.example" "$zeppPath\.env"
notepad "$zeppPath\.env"
$env:ZEPP_MCP_PATH = $zeppPath
running-coach
```

Añade tu correo y contraseña de Zepp en el `.env` local y nunca los compartas ni
los subas al repositorio. El coach activa Zepp únicamente cuando
`ZEPP_MCP_PATH` apunta al checkout; si no está configurado, sigue funcionando
con los cálculos locales.

Por privacidad y seguridad, el coach solo habilita resúmenes diarios, sueño,
frecuencia cardíaca, lista de entrenamientos, umbrales y composición corporal.
No habilita consultas GET arbitrarias ni detalles de entrenamiento que pueden
incluir GPS. El servidor consulta la API privada/no oficial de Zepp y puede dejar
de funcionar si cambia; los errores de inicio de sesión cuentan para un límite
compartido de intentos, así que no reintentes credenciales dudosas.

**Aviso de privacidad:** el servidor Zepp es local, pero las respuestas de salud
que el coach use se envían a Copilot para generar la respuesta. Solo conéctalo si
aceptas ese tratamiento de datos.

En la conversación, escribe `/salir` para terminar. También puedes ejecutarlo sin
instalar el comando:

```powershell
python -m running_coach.cli
```

## Alcance de esta fase

- Conversación en español con el perfil descrito en [PROJECT.md](PROJECT.md).
- Las herramientas locales calculan ritmo medio (distancia y duración) y tiempo
  estimado (distancia y ritmo constante), con parámetros validados.
- La integración Zepp es opcional; no hay conexión a Garmin ni Google Calendar.
- Sin memoria propia entre sesiones.
- El coach no diagnostica lesiones ni sustituye atención médica; evita recomendar
  correr con dolor y señala cuándo buscar valoración profesional.

No compartas credenciales de Zepp en el chat; configúralas únicamente en el `.env`
local del servidor Zepp. No hay conexión a Garmin ni Google Calendar.

## Pruebas

```powershell
python -m unittest discover -s tests
```
