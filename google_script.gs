/**
 * Puente GRATUITO entre "Mi Minion" y Google Calendar.
 * Se pega en https://script.google.com con la cuenta de Google cuyo calendario quieres usar.
 * No necesita Google Cloud ni tarjeta. Pasos completos en GUIA_GOOGLE.md.
 *
 * Puede leer varios calendarios (también los que te han compartido, si los tienes añadidos en
 * tu Google Calendar) y crear eventos con el color y el calendario que elijas en la app.
 */

// ============ CONFIGURA ESTO ============
var CLAVE = "CAMBIA_ESTO_POR_UNA_CLAVE_LARGA";  // la MISMA que GOOGLE_SCRIPT_CLAVE en config.py
var ID_CALENDARIO = "";                          // vacío = calendario principal de esta cuenta
// ========================================

var MARCA = "— Creado por Mi Minion";            // así reconoce la app los eventos que creó ella
var MARCA_NORMAL = "— Evento normal";            // los que no son fecha especial llevan además esto
var TZ = Session.getScriptTimeZone();

// Colores de evento de Google Calendar (1-11), para devolver el color de cada evento
var COLORES_EVENTO = {
  "1": "#a4bdfc", "2": "#7ae7bf", "3": "#dbadff", "4": "#ff887c", "5": "#fbd75b",
  "6": "#ffb878", "7": "#46d6db", "8": "#e1e1e1", "9": "#5484ed", "10": "#51b749",
  "11": "#dc2127"
};

// Se ejecuta UNA vez a mano para dar permiso al script (ver guía).
function autorizar() {
  Logger.log("Calendario: " + calendario_("").getName());
  Logger.log("Calendarios visibles: " + CalendarApp.getAllCalendars().length);
}

// Calendario por id; sin id, el principal (o el de ID_CALENDARIO)
function calendario_(id) {
  var cal;
  if (id) cal = CalendarApp.getCalendarById(id);
  else cal = ID_CALENDARIO ? CalendarApp.getCalendarById(ID_CALENDARIO)
                           : CalendarApp.getDefaultCalendar();
  if (!cal) throw new Error("No encuentro ese calendario" + (id ? " (" + id + ")" : "") +
                            ". Revisa que lo tengas añadido en tu Google Calendar.");
  return cal;
}

function respuesta_(objeto) {
  return ContentService.createTextOutput(JSON.stringify(objeto))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  try {
    var p = (e && e.parameter) ? e.parameter : {};
    if (!CLAVE || CLAVE === "CAMBIA_ESTO_POR_UNA_CLAVE_LARGA") {
      return respuesta_({ ok: false, error: "Falta poner tu CLAVE en el script." });
    }
    if (p.clave !== CLAVE) return respuesta_({ ok: false, error: "Clave incorrecta." });

    if (p.accion === "ping") return respuesta_({ ok: true });
    if (p.accion === "calendarios") return respuesta_({ ok: true, calendarios: calendarios_() });
    if (p.accion === "listar") return respuesta_({ ok: true, eventos: listar_(p) });
    if (p.accion === "crear") return respuesta_({ ok: true, id: crear_(p) });
    if (p.accion === "borrar") return respuesta_({ ok: true, borrado: borrar_(p.id, p.calendario) });
    return respuesta_({ ok: false, error: "Acción desconocida." });
  } catch (err) {
    return respuesta_({ ok: false, error: String(err) });
  }
}

// Lista de calendarios de la cuenta (propios y compartidos) con su color
function calendarios_() {
  var todos = CalendarApp.getAllCalendars();
  var principal = calendario_("").getId();
  var salida = [];
  for (var i = 0; i < todos.length; i++) {
    var c = todos[i];
    salida.push({
      id: c.getId(),
      nombre: c.getName(),
      color: c.getColor(),
      propio: c.isOwnedByMe(),
      seleccionado: c.isSelected(),       // los que tienes marcados en Google Calendar
      principal: c.getId() === principal
    });
  }
  return salida;
}

// Convierte "2026-11-30" en una fecha local
function fechaIso_(texto) {
  var t = String(texto).split("-");
  var d = new Date(parseInt(t[0], 10), parseInt(t[1], 10) - 1, parseInt(t[2], 10));
  if (isNaN(d.getTime())) throw new Error("Fecha no válida: " + texto);
  return d;
}

// Color de un evento: el suyo si lo tiene; si no, el de su calendario
function colorEvento_(ev, colorCalendario) {
  var c = "";
  try { c = String(ev.getColor() || ""); } catch (err) { c = ""; }
  return COLORES_EVENTO[c] || colorCalendario;
}

// Eventos de un rango (desde/hasta, ambos incluidos) o, si no se indica, los próximos "dias" días.
// "cals" = ids de calendarios separados por comas; vacío = el calendario principal.
function listar_(p) {
  var inicio, fin;
  if (p.desde && p.hasta) {
    inicio = fechaIso_(p.desde);
    fin = fechaIso_(p.hasta);
    fin.setDate(fin.getDate() + 1);                 // el último día entero
  } else {
    inicio = new Date();
    inicio.setHours(0, 0, 0, 0);
    fin = new Date(inicio.getTime() + parseInt(p.dias || "60", 10) * 86400000);
  }
  var ids = p.cals ? String(p.cals).split(",") : [""];
  var salida = [];
  for (var k = 0; k < ids.length; k++) {
    var cal;
    try { cal = calendario_(ids[k]); } catch (err) { continue; }   // calendario que ya no existe
    var colorCal = cal.getColor();
    var eventos = cal.getEvents(inicio, fin);
    for (var i = 0; i < eventos.length && salida.length < 400; i++) {
      var ev = eventos[i];
      var todoDia = ev.isAllDayEvent();
      var comienzo = todoDia ? ev.getAllDayStartDate() : ev.getStartTime();
      var descripcion = ev.getDescription() || "";
      var deLaApp = descripcion.indexOf(MARCA) >= 0;
      salida.push({
        id: ev.getId(),
        titulo: ev.getTitle(),
        fecha: Utilities.formatDate(comienzo, TZ, "yyyy-MM-dd"),
        hora: todoDia ? "" : Utilities.formatDate(comienzo, TZ, "HH:mm"),
        todoDia: todoDia,
        deLaApp: deLaApp,
        especial: deLaApp && descripcion.indexOf(MARCA_NORMAL) < 0,
        color: colorEvento_(ev, colorCal),
        calendarioId: cal.getId(),
        calendario: cal.getName()
      });
    }
  }
  return salida;
}

// Primera fecha del evento anual: el año original si lo hay, si no la próxima
function primeraFecha_(dia, mes, anio, hoy) {
  var hoy0 = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  var candidatos = [];
  if (anio) candidatos.push(anio);
  for (var i = 0; i < 9; i++) candidatos.push(hoy.getFullYear() + i);
  for (var k = 0; k < candidatos.length; k++) {
    var a = candidatos[k];
    var d = new Date(a, mes - 1, dia);
    if (d.getMonth() !== mes - 1) continue;          // 29 de febrero en año no bisiesto
    if (anio && a === anio) return d;
    if (d >= hoy0) return d;
  }
  return new Date(hoy.getFullYear() + 1, mes - 1, Math.min(dia, 28));
}

// Crea un evento. Parámetros:
//   nombre, dia, mes, anio(opc), mensaje(opc)
//   tipo: "especial" (por defecto) o "normal"
//   repetir: "1" (cada año, por defecto) o "0"
//   hora: "HH:MM" (opc; solo eventos normales; si no, es de todo el día)
//   color: "1".."11" (opc; si no, el color del calendario)
//   calendario: id (opc; si no, el principal)
//   recordatorio: minutos (opc; para eventos de todo el día)
function crear_(p) {
  var dia = parseInt(p.dia, 10), mes = parseInt(p.mes, 10);
  var anio = p.anio ? parseInt(p.anio, 10) : 0;
  if (!p.nombre || !(mes >= 1 && mes <= 12) || !(dia >= 1 && dia <= 31)) {
    throw new Error("Faltan datos de la fecha.");
  }
  var normal = p.tipo === "normal";
  var repetir = p.repetir !== "0";
  var cal = calendario_(p.calendario);
  var titulo = String(p.nombre).substring(0, 100);
  var descripcion = (p.mensaje ? p.mensaje + "\n\n" : "") + MARCA + (normal ? "\n" + MARCA_NORMAL : "");
  var opciones = { description: descripcion };
  var inicio = primeraFecha_(dia, mes, anio, new Date());

  var conHora = normal && /^\d{1,2}:\d{2}$/.test(p.hora || "");
  var evento;
  if (conHora) {
    var hm = p.hora.split(":");
    var h = parseInt(hm[0], 10), m = parseInt(hm[1], 10);
    if (h > 23 || m > 59) throw new Error("La hora no es válida.");
    var comienzo = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate(), h, m);
    var fin = new Date(comienzo.getTime() + 60 * 60000);          // dura 1 hora
    evento = repetir
      ? cal.createEventSeries(titulo, comienzo, fin, CalendarApp.newRecurrence().addYearlyRule(), opciones)
      : cal.createEvent(titulo, comienzo, fin, opciones);
  } else {
    evento = repetir
      ? cal.createAllDayEventSeries(titulo, inicio, CalendarApp.newRecurrence().addYearlyRule(), opciones)
      : cal.createAllDayEvent(titulo, inicio, opciones);
  }

  if (p.color && COLORES_EVENTO[String(p.color)]) evento.setColor(String(p.color));

  var minutos = parseInt(p.recordatorio || "0", 10);
  if (conHora) {
    evento.removeAllReminders();
    evento.addPopupReminder(30);                                   // 30 minutos antes
  } else if (minutos > 0) {
    evento.removeAllReminders();
    evento.addPopupReminder(minutos);   // 900 = el día antes a las 9:00 (evento de todo el día)
  }
  return evento.getId();
}

// Solo borra eventos creados por Mi Minion (nunca los demás del calendario)
function borrar_(id, calendarioId) {
  var cal = calendario_(calendarioId);
  var serie = cal.getEventSeriesById(id);
  var objeto = serie || cal.getEventById(id);
  if (!objeto) return false;
  if ((objeto.getDescription() || "").indexOf(MARCA) < 0) {
    throw new Error("Ese evento no lo creó Mi Minion, no lo borro.");
  }
  if (serie) serie.deleteEventSeries(); else objeto.deleteEvent();
  return true;
}
