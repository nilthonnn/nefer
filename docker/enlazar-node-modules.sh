#!/usr/bin/env bash
# Enlaza los node_modules preinstalados en la imagen con el checkout del repo.
#
#   enlazar-node-modules <ruta del proyecto Remotion> <nombre en /opt/remotion>
#   enlazar-node-modules shorts-factory/remotion shorts-factory
#
# Solo enlaza si el package-lock.json del checkout es idéntico al de la
# imagen. Si difiere (un PR que cambia dependencias antes de que exista su
# imagen), instala con `npm ci` para no probar con dependencias equivocadas.
set -euo pipefail

proyecto="${1:?ruta del proyecto Remotion}"
nombre="${2:?nombre del proyecto en /opt/remotion}"
origen="/opt/remotion/${nombre}"

if [ ! -f "${proyecto}/package-lock.json" ]; then
  echo "::error::No existe ${proyecto}/package-lock.json" >&2
  exit 1
fi

if [ -d "${origen}/node_modules" ] && cmp -s "${proyecto}/package-lock.json" "${origen}/package-lock.json"; then
  rm -rf "${proyecto}/node_modules"
  ln -s "${origen}/node_modules" "${proyecto}/node_modules"
  echo "node_modules de ${proyecto}: preinstalados en la imagen"
else
  echo "::warning::package-lock.json de ${proyecto} distinto al de la imagen; se ejecuta npm ci"
  (cd "${proyecto}" && npm ci --no-audit --no-fund)
fi
