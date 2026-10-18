# AI Running Coach

Primera fase del proyecto: un agente conversacional sencillo para running y
recomposición corporal, conectado a GitHub Copilot mediante el SDK oficial de
Python.

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

En la conversación, escribe `/salir` para terminar. También puedes ejecutarlo sin
instalar el comando:

```powershell
python -m running_coach.cli
```

## Alcance de esta fase

- Conversación en español con el perfil descrito en [PROJECT.md](PROJECT.md).
- Sin herramientas ni integraciones con dispositivos o calendarios; el proyecto no
  incorpora memoria propia entre sesiones.
- El coach no diagnostica lesiones ni sustituye atención médica; evita recomendar
  correr con dolor y señala cuándo buscar valoración profesional.

La Fase 1 no importa datos de Garmin, Amazfit/Zepp ni Google Calendar; no compartas
información sensible en el chat.

## Pruebas

```powershell
python -m unittest discover -s tests
```
