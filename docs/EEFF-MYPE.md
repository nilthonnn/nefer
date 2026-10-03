# Estados financieros para MYPE

Aplicación web, instalable y sin conexión, que arma el **Estado de Resultados**
y el **Estado de Situación Financiera** de una micro o pequeña empresa peruana,
con el formato de la SMV y el Plan Contable General Empresarial (PCGE 2019).

Se abre en `docs/eeff/` (publicada: `https://nilthonnn.github.io/nefer/eeff/`).
Los datos se quedan en el equipo, en el navegador; nada sale a internet.

## Pantallas

| Pestaña | Qué hace |
|---|---|
| **Empresa** | RUC (con dígito verificador), razón social, régimen, actividad y trabajadores. Datos del ejercicio: fecha de corte, UIT, porción de largo plazo de la cuenta 45, ajustes tributarios y pagos a cuenta. |
| **Saldos** | Dos formas de ingresar lo mismo: *Rápido por rubros* para el dueño (caja, clientes, mercadería, proveedores, ventas…) y *Balance de comprobación* a dos dígitos del PCGE para el contador. Se puede pegar desde Excel o del sistema contable: las subcuentas se suman a su cuenta. Indica si el balance cuadra y, si no, qué cuentas no se saldaron. |
| **Resultados** | Estado de resultados por función, comparado con el año anterior. |
| **Situación financiera** | Activo, pasivo y patrimonio, corriente y no corriente, con la comprobación Activo = Pasivo + Patrimonio. |
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

Las tasas, los topes y la UIT (S/ 5,500 en 2026) se pueden revisar en la propia app.
Es una herramienta de gestión y de preparación: la declaración la firma el contador.

## Pruebas

`tests/test_eeff_navegador.py` conduce la app en Chromium: el ejemplo cuadra en los
dos ejercicios, cada régimen da su impuesto, el RUC se valida, lo pegado se suma
bien, lo ingresado sobrevive a una recarga, la página entra en un teléfono y la
impresión sale sin formularios.

```bash
python -m pytest -q tests/test_eeff_navegador.py
```
