# Sistema de animaciones del perfil

Los cinco módulos visibles del README se generan dentro del propio repositorio:

- assets/hero.gif y assets/hero.svg
- assets/chess.gif y assets/chess.svg
- assets/stack.gif y assets/stack.svg
- assets/projects.gif y assets/projects.svg
- assets/social.gif y assets/social.svg

El visitante nunca consulta una API ni depende de GitSkins. El workflow consulta
metadatos públicos, reconstruye los archivos terminados y los guarda en el
repositorio.

El workflow se ejecuta cada seis horas y también admite ejecución manual. En
modo automático usa una actualización estricta: si GitHub no responde, el job
falla de forma visible en vez de publicar silenciosamente un snapshot antiguo.

## Regeneración local

1. Instalar Python 3.12.
2. Instalar Pillow con requirements.txt.
3. Ejecutar scripts/generate_profile_assets.py.
4. Ejecutar scripts/validate_profile_assets.py.

La opción --offline usa data/profile-snapshot.json y permite una generación
determinista sin red.

## Metodología de Stack Repository Signal

La señal usa bytes reportados por GitHub Linguist, normalizados únicamente entre
las doce tecnologías visibles. Excluye forks, repositorios archivados y copias
conocidas configuradas en data/profile.json.

El porcentaje no representa experiencia, dominio ni tiempo trabajado. Java y C
permanecen como competencias declaradas y muestran 0.0% mientras no exista código
público detectable. C++ ya se detecta mediante Tlalne-Priority y su porcentaje se
recalcula automáticamente junto con el resto del stack.

El generador recorre todos los repositorios públicos propios, pagina el catálogo
completo y consulta la clasificación de lenguajes de GitHub Linguist. Excluye
forks, repositorios archivados, el repositorio del perfil y copias conocidas.

## Logotipos de tecnologías

Las doce tarjetas usan archivos de logotipo originales, sin redibujarlos ni
recolorearlos. Se guardan localmente en `assets/icons/` para que el README no
dependa de un CDN al visualizarse. La colección base es Devicon `v2.17.0`,
fijada al commit `54cfe13ac10eaa1ef817a343ab0a9437eb3c2e08`; su licencia MIT
se incluye junto a los recursos. Los nombres y marcas pertenecen a sus
respectivos propietarios y se usan únicamente con fines identificativos.

## Selección de proyectos

El generador valora actividad, descripción, tamaño y estrellas. KASA Service
Tracker se conserva como proyecto esencial porque su repositorio aún no tiene
descripción pública ni estrellas; los otros espacios siguen compitiendo por la
señal automática. Los textos cortos corregidos viven en data/profile.json,
incluido el stack real de sistema-becas: PHP, PDO y MySQL/MariaDB.

La animación conserva seis tarjetas para mantener una lectura clara. Debajo se
genera una lista desplegable con todos los proyectos públicos elegibles. El
límite visual vive en `data/profile.json` y puede modificarse sin alterar la
lógica de consulta.

## Iconos de interfaz

Hero usa el ancla facilitada por el propietario del perfil. Los iconos de
GitHub, WhatsApp y ubicación proceden de Bootstrap Icons `v1.13.1` (MIT) y se
guardan localmente en `assets/icons/social/` junto con su licencia.
