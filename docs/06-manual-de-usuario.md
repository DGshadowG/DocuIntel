# 06 — Manual de Usuario

**DocuIntel — Sistema Inteligente de Gestión y Análisis Documental**

Este manual explica, paso a paso, cómo usar el sistema. Las capturas
referenciadas están en `evidence/screenshots/` y corresponden a la aplicación
real en funcionamiento.

---

## 1. Acceder al sistema

1. Abra su navegador en **http://localhost:5173** (o la URL que le entregue su
   administrador).
2. Escriba su **correo electrónico** y **contraseña** y pulse **Iniciar sesión**
   (captura `01-login.png`).
3. Si los datos son incorrectos verá "Correo o contraseña incorrectos".
   Si su cuenta está inactiva, contacte al administrador.
4. Al ingresar llegará al **Dashboard** (captura `02-dashboard.png`).

Para salir, pulse **Cerrar sesión** en la esquina superior derecha.

## 2. Crear un repositorio

Un repositorio es una carpeta inteligente que agrupa documentos y define quién
puede verlos.

1. En el menú, entre a **Repositorios** (captura `03-repositorios.png`).
2. Pulse **Nuevo repositorio**, escriba un nombre (mínimo 2 caracteres) y una
   descripción opcional, y pulse **Crear repositorio**.
3. El repositorio aparece en su lista. Usted queda como **propietario**.

**Compartir:** dentro del repositorio, en el panel **Miembros**, escriba el
correo de un usuario registrado y pulse **Agregar**. Para retirar a alguien,
pulse **Quitar** junto a su nombre (el propietario no puede quitarse).

## 3. Cargar documentos

1. Entre al repositorio (captura `04-repositorio-detalle.png`).
2. En la zona **"Cargar documentos (PDF, DOCX o TXT)"** pulse
   **Seleccionar archivos**. Puede elegir varios a la vez (hasta 20; máximo
   20 MB por archivo).
3. Verá la notificación "documento(s) cargado(s); el procesamiento inició".

Si el archivo no es PDF/DOCX/TXT real, está vacío o excede el tamaño, el
sistema lo rechaza con un mensaje claro y no se guarda nada.

## 4. Consultar estados de procesamiento

Cada documento pasa por: **Pendiente → En cola → Procesando → Completado**
(o **Fallido**). La tabla del repositorio se actualiza sola cada pocos
segundos (captura `05-carga-procesada.png`).

Si un documento queda **Fallido**, ábralo para ver el motivo técnico (por
ejemplo: "El PDF no contiene texto extraíble (posiblemente escaneado)") y use
**Reprocesar** para intentarlo de nuevo.

## 5. Ver los resultados de un documento

Abra cualquier documento desde una tabla o búsqueda (captura
`06-documento-detalle.png`). Verá:

- **Estado**, tipo, tamaño, páginas, fragmentos indexados y quién lo cargó.
- **Categoría** asignada por la IA, con su porcentaje de confianza y el modelo
  usado. Si la IA se equivocó, pulse **Corregir categoría** y elija la
  correcta — el sistema recuerda también lo que la IA predijo.
- **Resumen generado por IA** del contenido.
- **Datos extraídos** según el tipo: factura (proveedor, número, fechas,
  subtotal, impuestos, total, moneda), contrato (partes, objeto, fechas,
  duración, valor, obligaciones) u hoja de vida (nombre, perfil, educación,
  experiencia, habilidades, idiomas). "No detectado" significa que ese dato no
  aparece en el documento.
- **Texto extraído** (pulse "Mostrar") y el **historial de procesamiento** con
  intentos, duración y errores.

## 6. Buscar

Entre a **Buscar** y escriba su consulta.

- **Textual** (captura `07-busqueda-textual.png`): encuentra coincidencias
  exactas de sus palabras; los términos aparecen resaltados y cada resultado
  indica documento, repositorio y página.
- **Semántica (IA)** (captura `08-busqueda-semantica.png`): encuentra
  contenido por significado aunque no coincidan las palabras (ej.: buscar
  "personas con experiencia en programación" encuentra hojas de vida de
  desarrolladores). Los resultados muestran el porcentaje de similitud.

Puede filtrar por categoría y formato. Solo verá documentos de repositorios a
los que tiene acceso.

## 7. Preguntar a sus documentos (Consulta IA)

1. Entre a **Consulta IA**, elija el repositorio y pulse **Nueva conversación**.
2. Escriba una pregunta en lenguaje natural, por ejemplo:
   *"¿Cuál es el total a pagar de la factura FV-2024-100?"* y pulse
   **Preguntar**.
3. La respuesta llega con **Fuentes citadas**: cada fuente indica el documento,
   la página y el fragmento usado; puede hacer clic para abrir el documento
   (captura `09-chat-rag-citas.png`).
4. Si la información no está en los documentos, el sistema responde
   **"No se encontró evidencia suficiente en los documentos"** en lugar de
   inventar (captura `10-chat-sin-evidencia.png`).
5. Sus conversaciones quedan en el **Historial** del panel izquierdo.

## 8. Descargar y eliminar

- **Descargar:** botón **Descargar** en el detalle del documento — recibe el
  archivo original intacto.
- **Eliminar documento:** botón **Eliminar** en el detalle; se pide
  confirmación. Se borra el archivo y todos sus resultados de IA.
- **Eliminar repositorio:** botón **Eliminar** en el repositorio; la
  confirmación indica cuántos documentos se perderán. Esta acción no se puede
  deshacer.

## 9. Interpretar el dashboard

(captura `02-dashboard.png`)

- **Tarjetas superiores:** repositorios y documentos a los que tiene acceso,
  cuántos procesados y fallidos, y el tiempo medio de procesamiento.
- **Por categoría / formato / estado:** distribución de sus documentos.
- **Cargas de los últimos 14 días:** barras por día.
- **Actividad reciente:** últimos documentos con su estado.
- **Errores recientes:** documentos fallidos con el motivo (clic para abrir).

## 10. Administración (solo administradores)

- **Usuarios:** crear cuentas (correo, nombre, contraseña de mínimo 8
  caracteres, rol), activar/desactivar usuarios. No puede desactivarse a sí
  mismo.
- **Auditoría:** registro de todas las acciones (quién, qué, cuándo, desde qué
  IP), con filtro por tipo de acción.

## 11. Solución de problemas comunes

| Problema | Qué hacer |
|----------|-----------|
| "Correo o contraseña incorrectos" | Verifique mayúsculas; si persiste, pida al admin restablecer su contraseña |
| La sesión se cierra sola | El token expiró (8 h por defecto); vuelva a iniciar sesión |
| "Formato no permitido" al cargar | Solo PDF, DOCX y TXT reales; renombrar la extensión no funciona |
| "supera el límite de 20 MB" | Divida el archivo o pida al admin subir `MAX_UPLOAD_MB` |
| Documento **Fallido**: "PDF no contiene texto extraíble" | Es un PDF escaneado (imagen); conviértalo con OCR externo y vuelva a cargarlo |
| Documento **Fallido**: "proveedor de IA" | El servicio de IA no respondió; use **Reprocesar** cuando esté disponible |
| El chat responde "sin evidencia suficiente" | La respuesta no está en los documentos del repositorio elegido; verifique el repositorio o reformule |
| "No tiene acceso a este repositorio" | Pida al propietario que lo agregue como miembro |
| Página en blanco o error de interfaz | Pulse "Recargar página"; si persiste, informe al administrador con la hora del error |
