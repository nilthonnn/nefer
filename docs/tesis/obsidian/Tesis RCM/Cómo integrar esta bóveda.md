---
tags: [ayuda]
---

# Cómo integrar esta bóveda
Hay tres formas. Elige una.

## A. Usarla como bóveda propia (la más simple)
1. Descomprime `Boveda_Obsidian_Tesis_RCM.zip`.
2. Obsidian → icono de bóvedas (abajo a la izquierda) → **Abrir carpeta como bóveda** → elige `Tesis RCM`.
3. Si pregunta «¿Confiar en el autor?», acepta (no hay complementos de terceros, solo nativos).
4. Abre [[00 Inicio]]. El mapa visual es `Mapa de la sustentación.canvas`.

## B. Unirla a tu bóveda actual
1. Cierra Obsidian.
2. Copia la carpeta `Tesis RCM` **dentro** de tu bóveda (en la raíz).
3. Borra la carpeta oculta `Tesis RCM/.obsidian` (es la configuración de esta bóveda; la tuya no se toca).
4. Abre tu bóveda. Usa el mapa **`Mapa de la sustentación (bóveda unida).canvas`** (el otro mapa solo funciona en la opción A).
5. Plantillas: Configuración → Plantillas → carpeta `Tesis RCM/Plantillas` (o copia sus dos archivos a tu carpeta de plantillas).
6. Revisa choques de nombres: si ya tienes notas llamadas igual (por ejemplo `RCM`, `MTBF`, `AMEF`, `00 Inicio`), los enlaces pueden ir a la nota equivocada. Busca cada nombre con Ctrl/Cmd + O; si hay dos, renombra la tuya o la de esta carpeta (Obsidian actualiza los enlaces solo si «Actualizar enlaces automáticamente» está activo).
7. Opcional: agrega a marcadores `00 Inicio`, el mapa, `Guion 20 min` y `Riesgos de defensa`.

## C. Sincronizarla desde GitHub (recibe mis actualizaciones)
1. Requisito: Git instalado (Windows: git-scm.com).
2. Clona solo esta rama en una carpeta nueva:
   `git clone --branch ccr-a8a0c1e4-dc1ise --single-branch https://github.com/nilthonnn/nefer.git`
3. En Obsidian, abre como bóveda la carpeta `nefer/docs/tesis/obsidian/Tesis RCM` (opción A).
4. Para actualizar: en la carpeta `nefer`, ejecuta `git pull`; o instala el complemento comunitario **Obsidian Git** y usa «Obsidian Git: Pull» (Ctrl/Cmd + P).
5. Si además quieres tenerla dentro de tu bóveda principal (opción B), copia de nuevo la carpeta después de cada actualización; no mezcles dos repositorios en la misma bóveda.

## En el celular (Android)
- Copia la carpeta descomprimida al teléfono y en Obsidian móvil elige **Abrir carpeta como bóveda**.
- Las diapositivas embebidas y el Canvas funcionan; Obsidian Git en móvil es más lento: para actualizar, vuelve a copiar la carpeta.

## Si algo no se ve
- Imágenes rotas: verifica que exista `Archivos/Diapositivas 20 min` y `Archivos/Diapositivas v9`.
- Enlaces en gris: hay un choque de nombres (paso B6) o falta una carpeta.
- Canvas vacío: estás usando el mapa de la opción equivocada (A o B).
