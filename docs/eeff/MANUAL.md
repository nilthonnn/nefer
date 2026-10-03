# Estados financieros para MYPE

Aplicación web, instalable y sin conexión, que arma el **Estado de Resultados**
y el **Estado de Situación Financiera** de una micro o pequeña empresa peruana,
con el formato de la SMV y el Plan Contable General Empresarial (PCGE 2019).

Se abre en `docs/eeff/` (publicada: `https://nilthonnn.github.io/nefer/eeff/`).
Los datos se quedan en el equipo, en el navegador; nada sale a internet.

Es un proyecto aparte de las actas: todo lo suyo está en esta carpeta (página,
iconos, QR, manual), no usa nada de fuera de ella y su prueba
(`tests/test_eeff_navegador.py`) corre en su propio job de CI. Para llevarla a
otro repositorio basta con copiar la carpeta y la prueba.

## Cómo se pensó: el algoritmo de Musk

1. **Cuestionar el requisito.** Lo que le cuesta tiempo a una MYPE no es
   «hacer los estados», sino dos cosas: transcribir el balance del contador y
   redactar qué significan los números.
2. **Borrar.** Firmas, ajustes tributarios y presentación quedaron plegados
   como opcionales. Para obtener los estados basta con los saldos.
3. **Simplificar.** Al abrirla por primera vez, tres caminos: subir el balance,
   llenarlo a mano o ver un ejemplo.
4. **Acelerar.** Se sube el Excel (.xlsx), CSV o TXT tal como sale del sistema
   contable: reconoce el formato de 8 y 10 columnas por su encabezado y no
   duplica las cuentas cuando vienen con sus subcuentas.
5. **Automatizar, al final.** El informe para el gerente se escribe solo, con
   reglas fijas; se copia o se manda por WhatsApp. Para ir más allá, la app
   prepara el texto para pegarlo en una IA (Claude, ChatGPT o Gemini) sin el RUC
   ni el nombre de la empresa: la IA se usa cuando la persona decide, sin claves
   ni costos dentro de la app.

## Pantallas

| Pestaña | Qué hace |
|---|---|
| **Empresa** | RUC (con dígito verificador), razón social, régimen, actividad y trabajadores. Datos del ejercicio: fecha de corte, UIT, porción de largo plazo de la cuenta 45, ajustes tributarios y pagos a cuenta. |
| **Saldos** | Dos formas de ingresar lo mismo: *Rápido por rubros* para el dueño (caja, clientes, mercadería, proveedores, ventas…) y *Balance de comprobación* a dos dígitos del PCGE para el contador. Se puede subir el archivo (.xlsx, CSV, TXT, también arrastrándolo) o pegarlo desde Excel: las subcuentas se suman a su cuenta y, si vienen la cuenta y sus subcuentas, cuenta sólo el detalle. Indica si el balance cuadra y, si no, qué cuentas no se saldaron. |
| **Resultados** | Estado de resultados por función, comparado con el año anterior. |
| **Situación financiera** | Activo, pasivo y patrimonio, corriente y no corriente, con la comprobación Activo = Pasivo + Patrimonio. |
| **Informe** | Resumen, salud financiera, impuestos y «qué hacer», escrito solo. Copiar, WhatsApp y texto listo para una IA. |
| **Tributos e indicadores** | Impuesto a la renta según el régimen, categoría Ley 30056, libros obligatorios y trece indicadores (liquidez, endeudamiento, márgenes, ROA, ROE, rotaciones) con semáforo. |

Abajo: **Imprimir / PDF** (A4, con membrete y firmas del gerente y del contador),
**Excel (CSV)** con los dos estados y el balance, y **Respaldo / Restaurar** en JSON.

## Cómo calcula

- **Gastos.** Si la empresa usa las cuentas por función 94, 95 y 97, se toman de
  ahí; si no, de las cuentas por naturaleza 62 a 68, repartidas entre ventas y
  administración con el porcentaje que se indique.
- **Costo de ventas.** La 69; sin ella, la 60 más la 61.
- **Impuesto a la renta.** Si la cuenta 88 tiene saldo, se presenta ese. Si no,
  se estima y se registra como pasivo para que el balance cuadre antes del cierre:
  - **RMT:** 10 % hasta 15 UIT de renta neta y 29.5 % sobre el exceso.
  - **Régimen General:** 29.5 %.
  - **RER:** 1.5 % de los ingresos netos.
  - **Nuevo RUS:** cuota de S/ 20 o S/ 50 al mes.
  La renta neta parte del resultado contable, más adiciones y menos deducciones,
  menos la participación de los trabajadores y las pérdidas compensables.
- **Participación de los trabajadores.** Sólo con más de 20 trabajadores: 10 % pesca,
  telecomunicaciones e industria; 8 % minería, comercio y restaurantes; 5 % las demás.
- **Saldos de signo cambiado.** Caja en negativo se presenta como sobregiro (pasivo);
  la 40 deudora como saldo a favor (activo).

Las tasas, los topes y la UIT (S/ 5,500 en 2026, D.S. 301-2025-EF) se pueden revisar en la propia app.
Es una herramienta de gestión y de preparación: la declaración la firma el contador.

## Pruebas

`tests/test_eeff_navegador.py` conduce la app en Chromium: el ejemplo cuadra en los
dos ejercicios, cada régimen da su impuesto, el RUC se valida, lo pegado se suma
bien (también desde un .xlsx real y en el formato de 10 columnas), el informe se
escribe solo y no manda el RUC a la IA, lo ingresado sobrevive a una recarga, la página entra en un teléfono y la
impresión sale sin formularios.

```bash
python -m pytest -q tests/test_eeff_navegador.py
```
