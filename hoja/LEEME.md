# Sistema NOVAVAULT: hoja, página y WhatsApp

Una hoja de Google manda sobre todo. Cambias un precio o marcas un perfume como agotado en la hoja y:

- **la página** (`/api/inventario`) lo muestra en menos de un minuto;
- **el bot de WhatsApp** (`/api/whatsapp`) lo sabe desde el siguiente mensaje;
- **los pedidos** que confirma el bot llegan a la pestaña **Pedidos** y te llega un correo.

```
Google Sheets ──(Apps Script: hoja/Codigo.gs)──> Vercel ──> página
      ▲                                            │
      └───── pedidos, chats y mensajes ◄── bot ◄───┴──> WhatsApp (Meta) + Claude
```

## 1. Crear la hoja (10 min)

1. Crea una hoja nueva en [sheets.google.com](https://sheets.google.com) y llámala **NOVAVAULT Inventario**.
2. **Archivo > Importar > Subir** y elige `hoja/Inventario.csv`. Elige **Reemplazar hoja actual**. Cambia el nombre de la pestaña a **Inventario**.
3. Otra vez **Archivo > Importar > Subir**, ahora `hoja/Datos.csv`, con **Insertar hojas nuevas**. Cambia el nombre de esa pestaña a **Datos**.

Las columnas de **Inventario**:

| Columna | Qué poner |
|---|---|
| `id` | No lo cambies: une el perfume con su foto en `img/`. |
| `nombre`, `casa` | Como quieres que se vea. |
| `coleccion` | `árabe` o `diseñador`. |
| `estilos` | Separados por comas: `cálido`, `fresco`, `floral`, `intenso`. |
| `mas_buscado` | `sí` o `no`. |
| `estado` | `disponible`, `agotado` o `consultar` (el bot te pasa el chat en vez de responder). |
| `precio` | Precio de menudeo en dólares. Vacío = el bot no da precio y te pasa el chat. |
| `en_pagina` | `sí` para mostrarlo en la página (necesita foto en `img/`). |
| `descripcion_en`, `descripcion_es` | Las notas que ven los clientes; el bot también las usa. |

En **Datos** están el horario, los pagos, los envíos, las devoluciones y el mínimo de mayoreo. El bot solo afirma lo que diga ahí.

## 2. Conectar la hoja con Apps Script (10 min)

1. En la hoja: **Extensiones > Apps Script**. Borra lo que haya y pega todo `hoja/Codigo.gs`. Guarda.
2. **Configuración del proyecto** (engrane) **> Propiedades del script > Agregar**:
   - `TOKEN`: una clave larga e inventada (por ejemplo 40 letras y números al azar). No la compartas.
   - `CORREO`: el correo donde quieres recibir los avisos de pedidos.
3. Vuelve al editor, elige la función **configurar** y pulsa **Ejecutar**. Acepta los permisos. Se crean las pestañas **Pedidos**, **Chats** y **Mensajes**.
4. **Implementar > Nueva implementación > Aplicación web**, con **Ejecutar como: yo** y **Quién tiene acceso: cualquier usuario**. Copia la URL que termina en `/exec`.

Nadie puede leer ni escribir la hoja sin el `TOKEN`; la URL sola no basta.

Si cambias `Codigo.gs` después, usa **Implementar > Administrar implementaciones > editar > Nueva versión** para que la URL siga siendo la misma.

## 3. Variables en Vercel

En [vercel.com](https://vercel.com) > proyecto **novavault** > **Settings > Environment Variables**:

| Variable | Valor |
|---|---|
| `HOJA_URL` | La URL `/exec` del paso 2. |
| `HOJA_TOKEN` | El mismo `TOKEN` del paso 2. |

Con solo estas dos, **la página ya lee la hoja** después del siguiente despliegue. Si la hoja no responde, la página muestra el catálogo que trae `index.html`.

## 4. El bot de WhatsApp

### Clave de Claude

En [console.anthropic.com](https://console.anthropic.com) crea una API key y agrégala en Vercel como `ANTHROPIC_API_KEY`. El bot usa Claude Opus 5.5 con esfuerzo bajo; para gastar menos puedes poner `CLAUDE_MODEL` = `claude-sonnet-5-5` o `claude-haiku-5-5`.

### WhatsApp Cloud API (Meta)

1. En [developers.facebook.com](https://developers.facebook.com) crea una app de tipo **Business** y agrégale el producto **WhatsApp**.
2. Prueba primero con el **número de prueba gratis** que te da Meta, con tu propio celular como destinatario.
3. Copia a Vercel:
   - `WHATSAPP_PHONE_ID`: el *Phone number ID*.
   - `WHATSAPP_TOKEN`: un token permanente de un *usuario del sistema* (Configuración del negocio > Usuarios del sistema) con el permiso `whatsapp_business_messaging`. El token temporal de la página de inicio vence en 24 h.
   - `WHATSAPP_APP_SECRET`: **Configuración de la app > Básica > Clave secreta de la app**.
   - `WHATSAPP_VERIFY_TOKEN`: otra palabra inventada.
4. En **WhatsApp > Configuración > Webhook**: URL `https://novavault-chi.vercel.app/api/whatsapp`, token de verificación = tu `WHATSAPP_VERIFY_TOKEN`. Suscríbete al campo **messages**.
5. Vuelve a desplegar en Vercel y escríbele al número de prueba.

**Antes de conectar tu número real (+1 510 978 8240):** al pasar un número a la Cloud API, normalmente deja de funcionar en la app WhatsApp Business. Si Meta te ofrece conectarlo en modo **coexistencia** (seguir usando la app y la API con el mismo número), elígelo; así sigues contestando desde tu celular cuando el bot te pase un chat. Si no te lo ofrece, considera un número aparte para el bot. Revisa también los precios de Meta para mensajes de negocio.

## Uso diario

- **Inventario:** cambia `estado` y `precio` en la hoja. Listo.
- **Perfume nuevo:** agrega la fila. El bot lo conoce de inmediato; para que salga en la página hace falta subir su foto a `img/` con el mismo `id`.
- **Cuando el bot te pasa un chat** (pedido confirmado, mayoreo, quejas, preguntas sin respuesta): te llega un correo y en **Chats** ese cliente queda con `bot` = `pausado`. Contesta tú; cuando termines, escribe `activo` para que el bot vuelva a atenderlo.
- **Pedidos:** cada pedido confirmado llega con `estado` = `nuevo`. Cámbialo a `pagado`, `enviado`, etc. como te sirva.
- **Mensajes:** el historial de cada chat. Una conversación se reinicia después de 24 h sin mensajes.
