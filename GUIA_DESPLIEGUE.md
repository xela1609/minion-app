# Poner Mi Minion en internet (gratis) para instalarlo en el iPhone

Resultado: una dirección https (tipo `https://mi-minion.onrender.com`). Ella la abre en Safari →
Compartir → **Añadir a pantalla de inicio** y queda como una app.

## 1. Subir el código a GitHub (privado)
1. Crea cuenta en https://github.com y un repositorio **Private** llamado `mi-minion`.
2. **Add file → Upload files** y arrastra el contenido de la carpeta `minion_app`.
   ⚠️ **NO subas `config_local.py`** (lleva tus claves). Ya está en `.gitignore`, pero al subir a mano
   por web hay que dejarlo fuera tú.
3. Commit.

## 2. Crear el servicio en Render
1. Cuenta en https://render.com (entra con GitHub). Comprueba tú mismo en su web si piden tarjeta para el plan gratuito.
2. **New → Blueprint** (usa `render.yaml`) o **New → Web Service**: elige el repo, entorno **Docker**, plan **Free**.
3. En **Environment** pon (las claves van aquí, no en el repo):
   - `GOOGLE_SCRIPT_URL`, `GOOGLE_SCRIPT_CLAVE`
   - `CHAT_API_KEY` (Groq), `CHAT_API_URL`, `CHAT_MODELO`
   - `CHAT_PERSONALIDAD_EXTRA`, `NOMBRE_ELLA`, `CIUDAD`
   - `TZ` = `Europe/Madrid`
4. Deploy. Tarda unos minutos. Abre la URL: debe verse el Minion.

## 3. Instalar en el iPhone
Safari (tiene que ser Safari) → abrir la URL → botón Compartir → **Añadir a pantalla de inicio**.

## Cosas que debes saber
- **Se duerme** tras ~15 min sin uso; despertarla tarda ~1 min. Se puede mitigar con un pinger gratuito
  (UptimeRobot / cron-job.org) que abra la URL cada 10 min. Comprueba que el plan gratuito lo permita.
- Límite de ~750 h/mes en el plan gratuito.
- No hay disco: el estado (hambre, chat, calendarios marcados) se guarda en el navegador del móvil, no en el servidor.
- Si borra los datos de Safari, se pierde ese estado.
- Cambiar código = subir a GitHub y Render redespliega solo.
