#!/usr/bin/env bash
# Crea la llave con la que se firma el .apk de RD RENTAL. Se ejecuta UNA vez.
#
# Por que hace falta:
#   Android no instala nada sin firma, y solo deja actualizar una aplicacion
#   con una version firmada con LA MISMA llave. Sin llave propia, cada
#   compilacion sale con una distinta y el operario tiene que desinstalar la
#   app —y con ella las actas a medias— para poner la version nueva.
#
# Que hacer con lo que sale:
#   1. Guardar `firma-rd-rental.jks` en un sitio seguro y con copia. Si se
#      pierde, no hay forma de publicar una actualizacion: hay que empezar con
#      otra aplicacion y desinstalar la vieja en todos los telefonos.
#   2. NO meterlo en el repositorio. Esta en .gitignore por si acaso.
#   3. Copiar las cuatro claves que imprime en
#      github.com/<usuario>/<repo>/settings/secrets/actions
#
# Uso:
#   herramientas/crear-llave-android.sh [ruta-de-salida]

set -euo pipefail

salida="${1:-firma-rd-rental.jks}"
alias_llave="actas"

if [ -e "$salida" ]; then
  echo "ya existe $salida — no se toca." >&2
  echo "Si de verdad quiere una llave nueva, mueva la vieja antes." >&2
  exit 1
fi

command -v keytool >/dev/null || {
  echo "falta keytool: instale un JDK (apt install default-jdk)" >&2
  exit 1
}

# Una contrasena larga y al azar: nadie la va a teclear, viaja en un secreto.
clave="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40)"

keytool -genkeypair -v \
  -keystore "$salida" \
  -alias "$alias_llave" \
  -keyalg RSA -keysize 4096 \
  -validity 10000 \
  -storepass "$clave" -keypass "$clave" \
  -dname "CN=RD RENTAL Actas, OU=Campo, O=RD RENTAL, L=Lima, C=PE"

chmod 600 "$salida"

echo
echo "================================================================"
echo " Llave creada en: $salida"
echo " Guardela con copia de seguridad. Sin ella no hay actualizaciones."
echo "================================================================"
echo
echo "Ponga estos cuatro secretos en el repositorio"
echo "(Settings -> Secrets and variables -> Actions -> New repository secret):"
echo
echo "  ANDROID_ALMACEN_BASE64"
base64 -w0 "$salida" 2>/dev/null || base64 "$salida" | tr -d '\n'
echo
echo
echo "  ANDROID_CLAVE_ALMACEN"
echo "$clave"
echo
echo "  ANDROID_ALIAS"
echo "$alias_llave"
echo
echo "  ANDROID_CLAVE_LLAVE"
echo "$clave"
echo
echo "Huella de la firma (la que queda en los telefonos):"
keytool -list -v -keystore "$salida" -storepass "$clave" -alias "$alias_llave" \
  | grep -E "SHA256:|SHA1:" || true
