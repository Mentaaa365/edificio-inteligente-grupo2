// Dashboard del Grupo 2. JavaScript sin frameworks, en cinco partes:
//   1. Utilidades          2. Plano SVG desde grafo.json     3. Paneles (estado, alertas, tablas)
//   4. Gráficas Chart.js   5. Tiempo real: WebSocket y, si falla, sondeo cada segundo
"use strict";

// ============================================================ 1. utilidades
const $ = (sel) => document.querySelector(sel);
const SVG_NS = "http://www.w3.org/2000/svg";

let GRAFO = null;          // respuesta de /api/grafo/
let ultimoId = 0;          // id del último evento mostrado (para no repetir ni perder ninguno)
let eventosGrafica = [];   // eventos que muestran las gráficas, del más antiguo al más nuevo
const MAX_GRAFICA = 50;

// Número con coma decimal, como en los documentos del proyecto.
function fmt(valor, decimales = 2) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("es-EC", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

function hora(iso) {
  return new Date(iso).toLocaleString("es-EC", { dateStyle: "short", timeStyle: "medium" });
}

// Crea un elemento SVG con sus atributos.
function svg(tag, attrs = {}, texto = null) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (texto !== null) e.textContent = texto;
  return e;
}

// Crea una fila de tabla. Se usa textContent (nunca innerHTML) para que ningún dato se interprete como HTML.
function fila(celdas) {
  const tr = document.createElement("tr");
  for (const c of celdas) {
    const td = document.createElement("td");
    if (c && typeof c === "object") { td.textContent = c.texto; if (c.clase) td.className = c.clase; }
    else td.textContent = c;
    tr.appendChild(td);
  }
  return tr;
}

// Django exige la cookie csrftoken en los POST que hace el navegador.
// https://docs.djangoproject.com/en/5.2/howto/csrf/#using-csrf-protection-with-ajax
function csrf() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function pedir(url, opciones = {}) {
  const r = await fetch(url, opciones);
  const datos = await r.json();
  if (!r.ok) throw new Error(datos.error || r.statusText);
  return datos;
}

const zonas = () => GRAFO.nodos.filter((n) => n.tipo === "zona");
const pasillos = () => GRAFO.aristas.filter((a) => a.tipo === "pasillo");

// ============================================================ 2. plano SVG
// grafo.json usa metros con el eje y hacia arriba (norte). En SVG el eje y va hacia abajo,
// así que se invierte: y_svg = (y_max + margen) - y_m.
function dibujarPlano(elemento, resultado) {
  const MARGEN = 3;
  const xs = GRAFO.nodos.map((n) => n.x_m), ys = GRAFO.nodos.map((n) => n.y_m);
  const x0 = Math.min(...xs) - MARGEN, x1 = Math.max(...xs) + MARGEN;
  const y0 = Math.min(...ys) - MARGEN, y1 = Math.max(...ys) + MARGEN;
  const X = (n) => n.x_m - x0;
  const Y = (n) => y1 - n.y_m;
  const nodo = Object.fromEntries(GRAFO.nodos.map((n) => [n.id, n]));

  elemento.setAttribute("viewBox", `0 0 ${x1 - x0} ${y1 - y0}`);
  elemento.replaceChildren();

  // Punta de flecha para indicar el sentido de la evacuación.
  const idFlecha = `flecha-${elemento.id}`;
  const defs = svg("defs");
  const marcador = svg("marker", { id: idFlecha, viewBox: "0 0 10 10", refX: "5", refY: "5",
    markerWidth: "3", markerHeight: "3", orient: "auto-start-reverse" });
  marcador.appendChild(svg("path", { d: "M0,0 L10,5 L0,10 z", class: "flecha" }));
  defs.appendChild(marcador);
  elemento.appendChild(defs);

  const r = resultado || {};
  const bloqueos = new Set(r.bloqueos || []);
  const ocupadas = new Set(r.ocupadas || []);
  const aisladas = new Set(r.aristas_aisladas || []);
  const zonasAisladas = new Set(r.zonas_aisladas || []);
  const enRuta = new Set(Object.values(r.detalle || {}).flatMap((d) => d.aristas));
  const sentido = r.sentido || {};

  // Aristas: primero las puertas y luego los pasillos, para que estos queden encima.
  const aristas = [...GRAFO.aristas].sort((a, b) => (a.tipo === "puerta" ? -1 : 1) - (b.tipo === "puerta" ? -1 : 1));
  for (const a of aristas) {
    let clase = `arista ${a.tipo}`;
    if (bloqueos.has(a.id)) clase += " bloqueada";
    else if (aisladas.has(a.id)) clase += " aislada";
    else if (enRuta.has(a.id)) clase += " ruta";
    // Si la arista está en una ruta se dibuja desde -> hacia, con la flecha al final.
    let [desde, hacia] = sentido[a.id] && enRuta.has(a.id) ? sentido[a.id] : [a.u, a.v];
    const p = nodo[desde], q = nodo[hacia];
    const linea = svg("line", { x1: X(p), y1: Y(p), x2: X(q), y2: Y(q), class: clase });
    if (enRuta.has(a.id) && !bloqueos.has(a.id)) linea.setAttribute("marker-end", `url(#${idFlecha})`);
    linea.appendChild(svg("title", {}, `${a.id} · ${a.longitud_m} m${a.pulsador ? " · pulsador " + a.pulsador : ""}`));
    elemento.appendChild(linea);
    if (a.tipo === "pasillo") {
      const horizontal = Math.abs(Y(p) - Y(q)) < 0.1;
      elemento.appendChild(svg("text", {
        x: (X(p) + X(q)) / 2 + (horizontal ? 0 : 1.2),
        y: (Y(p) + Y(q)) / 2 + (horizontal ? -0.9 : 0.4), class: "etq-arista",
      }, a.id));
    }
  }

  // Nodos
  for (const n of GRAFO.nodos) {
    const x = X(n), y = Y(n);
    if (n.tipo === "salida") {
      elemento.appendChild(svg("rect", { x: x - 1.2, y: y - 1.2, width: 2.4, height: 2.4, rx: 0.3, class: "nodo-salida" }));
      elemento.appendChild(svg("text", { x, y, class: "etq-nodo", style: "fill:#fff" }, n.id));
      elemento.appendChild(svg("text", { x, y: y + 2.2, class: "etq-nombre" }, n.nombre));
    } else if (n.tipo === "interseccion") {
      elemento.appendChild(svg("circle", { cx: x, cy: y, r: 0.45, class: "nodo-cruce" }));
    } else {
      let clase = "nodo-zona";
      if (ocupadas.has(n.id)) clase += " ocupada";
      if (zonasAisladas.has(n.id)) clase += " zona-aislada";
      const c = svg("circle", { cx: x, cy: y, r: 1.15, class: clase });
      const d = (r.detalle || {})[n.id];
      c.appendChild(svg("title", {}, `${n.id} ${n.nombre}` +
        (d ? (d.salida ? ` → ${d.salida}, ${fmt(d.longitud_m, 0)} m` : " · aislada") : "")));
      elemento.appendChild(c);
      elemento.appendChild(svg("text", { x, y, class: "etq-nodo" }, n.id));
      elemento.appendChild(svg("text", { x, y: y + (n.y_m > 20 ? -1.7 : 2.0), class: "etq-nombre" }, n.nombre));
    }
  }
}

// ============================================================ 3. paneles
function llenarTablaRutas(tbody, resultado) {
  tbody.replaceChildren();
  if (!resultado) return;
  for (const z of zonas()) {
    const ruta = resultado.rutas[z.id];
    const d = resultado.detalle[z.id];
    if (!ruta) {
      tbody.appendChild(fila([`${z.id} ${z.nombre}`, { texto: "Aislada", clase: "aislada" }, "—", "—", "—", "—"]));
      continue;
    }
    tbody.appendChild(fila([
      `${z.id} ${z.nombre}`, ruta.ruta.replaceAll(">", " → "), fmt(d.costo_m), `${fmt(d.longitud_m, 0)} m`,
      `${fmt(d.tiempo_s, 1)} s`, d.salida,
    ]));
  }
}

function ponerEstado(elemento, estado) {
  elemento.textContent = estado.replaceAll("_", " ");
  elemento.className = elemento.className.replace(/\be-\S+/g, "").trim() + ` e-${estado}`;
}

function agregarAlerta(texto, nivel = "info") {
  const ul = $("#alertas");
  ul.querySelector(".vacio")?.remove();
  const li = document.createElement("li");
  li.className = nivel;
  li.textContent = `${new Date().toLocaleTimeString("es-EC")} · ${texto}`;
  ul.prepend(li);
  while (ul.children.length > 30) ul.lastChild.remove();
}

// Muestra en el plano principal un resultado del servidor (de un evento o de un escenario).
function mostrarEnPlano(resultado, origen) {
  $("#plano-origen").textContent = origen;
  dibujarPlano($("#plano"), resultado);
  llenarTablaRutas($("#tabla-rutas tbody"), resultado);
}

// Procesa un evento nuevo (llegue por WebSocket o por sondeo).
function procesarEvento(ev, { alertar = true, alHistorico = true } = {}) {
  if (ev.id <= ultimoId) return;          // ya mostrado
  ultimoId = ev.id;
  const e = ev.esp32, s = ev.servidor;

  ponerEstado($("#estado-texto"), e.estado);
  $("#dato-evento").textContent = `${e.evento} (#${ev.id}, ${ev.origen})`;
  $("#dato-hora").textContent = hora(ev.recibido);
  $("#dato-bloqueos").textContent = e.bloqueos.join(", ") || "ninguno";
  $("#dato-ocupadas").textContent = e.ocupadas.join(", ") || "ninguna";
  $("#dato-calculo").textContent = `${e.calculo_us} µs / ${s ? s.calculo_us : "—"} µs`;
  const dc = $("#dato-coincide");
  dc.textContent = s && s.coincide_esp32 ? "Sí" : "No";
  dc.className = s && s.coincide_esp32 ? "si" : "no";
  if (s) mostrarEnPlano(s, `· evento #${ev.id} ${e.evento}`);

  if (alertar) {
    if (e.estado === "SIN_RUTA") agregarAlerta("SIN RUTA: ninguna zona puede salir.", "critica");
    else if (e.estado === "RUTA_PARCIAL")
      agregarAlerta(`Ruta parcial: zonas aisladas ${s ? s.zonas_aisladas.join(", ") : e.aisladas}.`, "aviso");
    else if (e.evento === "B0") agregarAlerta("Alarma activada (B0).", "aviso");
    else if (e.evento === "B7") agregarAlerta("Sistema reiniciado (B7).");
    if (s && s.coincide_esp32 === false)
      agregarAlerta(`El ESP32 y el modelo NO coinciden: ${s.diferencias.join("; ")}`, "critica");
  }

  // El histórico y las gráficas solo se actualizan en vivo cuando no hay filtros aplicados.
  if (alHistorico && !filtrosActivos()) {
    $("#tabla-historico tbody").prepend(filaHistorico(ev));
    eventosGrafica.push(ev);
    if (eventosGrafica.length > MAX_GRAFICA) eventosGrafica.shift();
    actualizarGraficas();
  }
}

function filaHistorico(ev) {
  const e = ev.esp32, s = ev.servidor;
  const coincide = s ? s.coincide_esp32 : null;
  return fila([
    ev.id, hora(ev.recibido), ev.origen, e.evento, e.estado,
    e.bloqueos.join(", ") || "—", e.ocupadas.join(", ") || "—", e.aisladas, `${e.calculo_us} µs`,
    { texto: coincide ? "Sí" : "No", clase: coincide ? "si" : "no" },
  ]);
}

function filtrosActivos() {
  const f = new FormData($("#form-historico"));
  return ["desde", "hasta", "estado", "evento", "coincide"].some((k) => f.get(k));
}

async function cargarHistorico() {
  const parametros = new URLSearchParams();
  for (const [k, v] of new FormData($("#form-historico"))) if (v) parametros.set(k, v);
  const datos = await pedir(`/api/historico/?${parametros}`);
  const tbody = $("#tabla-historico tbody");
  tbody.replaceChildren(...datos.eventos.map(filaHistorico));
  $("#historico-total").textContent = `${datos.eventos.length} de ${datos.total} eventos.`;
  eventosGrafica = datos.eventos.slice(0, MAX_GRAFICA).reverse();
  actualizarGraficas();
  return datos;
}

async function cargarEscenarios() {
  const { escenarios } = await pedir("/api/escenarios/");
  const tbody = $("#tabla-escenarios tbody");
  tbody.replaceChildren();
  for (const esc of escenarios) {
    const tr = fila([esc.nombre, esc.descripcion, esc.estado_envio]);
    const td = document.createElement("td");
    const boton = document.createElement("button");
    boton.textContent = "Ejecutar";
    boton.addEventListener("click", () => ejecutarEscenario(esc.id, boton));
    td.appendChild(boton);
    tr.appendChild(td);
    tbody.appendChild(tr);
  }
}

async function ejecutarEscenario(id, boton) {
  boton.disabled = true;
  try {
    const datos = await pedir(`/api/escenarios/${id}/ejecutar/`, { method: "POST", headers: { "X-CSRFToken": csrf() } });
    // Si hay WebSocket, el mismo resultado llega también por ahí; mostrarlo dos veces no hace daño.
    mostrarEscenario(datos.ruta);
  } catch (err) {
    agregarAlerta(`No se pudo ejecutar el escenario: ${err.message}`, "critica");
  } finally {
    boton.disabled = false;
  }
}

function mostrarEscenario(ruta) {
  mostrarEnPlano(ruta, `· escenario ${ruta.escenario} (calculado en el servidor)`);
  agregarAlerta(`Escenario ${ruta.escenario} ejecutado: ${ruta.estado.replaceAll("_", " ")}. Pendiente para el ESP32.`);
  cargarEscenarios();
}

// ============================================================ simulador
function prepararSimulador() {
  const casilla = (contenedor, valor, texto) => {
    const l = document.createElement("label");
    const i = document.createElement("input");
    i.type = "checkbox"; i.value = valor;
    l.append(i, ` ${texto}`);
    contenedor.appendChild(l);
  };
  pasillos().forEach((a) => casilla($("#sim-bloqueos"), a.id, a.id));
  zonas().forEach((z) => casilla($("#sim-ocupadas"), z.id, z.id));
  const p = GRAFO.parametros;
  $("#sim-reiniciar").addEventListener("click", () => {
    document.querySelectorAll("#form-simulador input[type=checkbox]").forEach((c) => (c.checked = false));
    $("#sim-alfa").value = p.alfa_pct;
    $("#sim-beta").value = p.beta_pct;
    simular();
  });
  let espera = null;   // pequeña espera para no pedir un cálculo por cada píxel del deslizador
  $("#form-simulador").addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(simular, 120); });
  simular();
}

async function simular() {
  const marcadas = (sel) => [...document.querySelectorAll(`${sel} input:checked`)].map((c) => c.value);
  const alfa = Number($("#sim-alfa").value), beta = Number($("#sim-beta").value);
  $("#sim-alfa-valor").textContent = fmt(alfa / 100);
  $("#sim-beta-valor").textContent = fmt(beta / 100);
  try {
    const r = await pedir("/api/simular/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bloqueos: marcadas("#sim-bloqueos"), ocupadas: marcadas("#sim-ocupadas"), alfa_pct: alfa, beta_pct: beta }),
    });
    ponerEstado($("#sim-estado"), r.estado);
    dibujarPlano($("#plano-sim"), r);
    llenarTablaRutas($("#tabla-sim tbody"), r);
  } catch (err) {
    $("#sim-estado").textContent = `Error: ${err.message}`;
  }
}

// ============================================================ 4. gráficas (Chart.js)
const graficas = {};

function color(variable) {
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

function crearGraficas() {
  if (!window.Chart) {   // sin internet no carga el CDN: el resto del dashboard sigue funcionando
    document.querySelector(".graficas").textContent = "Chart.js no se pudo cargar (¿sin internet?).";
    return;
  }
  Chart.defaults.color = color("--suave");
  Chart.defaults.borderColor = color("--borde");
  const base = (titulo, ejeY) => ({
    responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { title: { display: true, text: titulo }, legend: { position: "bottom" } },
    scales: { y: { beginAtZero: true, title: { display: true, text: ejeY } } },
  });
  graficas.calculo = new Chart($("#graf-calculo"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "ESP32", data: [], borderColor: color("--azul"), backgroundColor: color("--azul"), tension: 0.2 },
      { label: "Servidor (Python)", data: [], borderColor: color("--suave"), backgroundColor: color("--suave"), tension: 0.2 },
    ] },
    options: base("Tiempo de cálculo de Dijkstra", "µs"),
  });
  graficas.recorrido = new Chart($("#graf-recorrido"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "Recorrido medio", data: [], borderColor: color("--verde"), backgroundColor: color("--verde"), tension: 0.2 },
      { label: "Recorrido máximo", data: [], borderColor: color("--rojo"), backgroundColor: color("--rojo"), tension: 0.2 },
    ] },
    options: base("Recorrido de las zonas con ruta", "metros"),
  });
  graficas.aisladas = new Chart($("#graf-aisladas"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Zonas aisladas", data: [], backgroundColor: color("--ambar") }] },
    options: { ...base("Zonas aisladas por evento", "zonas"), scales: { y: { beginAtZero: true, max: 8, ticks: { stepSize: 1 } } } },
  });
}

function actualizarGraficas() {
  if (!graficas.calculo) return;
  const etiquetas = eventosGrafica.map((ev) => `#${ev.id} ${ev.esp32.evento}`);
  const longitudes = (ev) => Object.values(ev.servidor?.detalle || {}).map((d) => d.longitud_m).filter((x) => x !== null);
  const media = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  const series = {
    calculo: [eventosGrafica.map((ev) => ev.esp32.calculo_us), eventosGrafica.map((ev) => ev.servidor?.calculo_us ?? null)],
    recorrido: [eventosGrafica.map((ev) => media(longitudes(ev))),
                eventosGrafica.map((ev) => (longitudes(ev).length ? Math.max(...longitudes(ev)) : null))],
    aisladas: [eventosGrafica.map((ev) => ev.esp32.aisladas)],
  };
  for (const [nombre, datos] of Object.entries(series)) {
    const g = graficas[nombre];
    g.data.labels = etiquetas;
    datos.forEach((d, i) => (g.data.datasets[i].data = d));
    g.update();
  }
}

// ============================================================ 5. tiempo real
// Se intenta WebSocket (Django Channels). Si no conecta o se cae, se pasa a sondeo:
// pedir /api/historico/?despues_de=<último id> cada segundo, y reintentar el WebSocket cada 5 s.
// https://channels.readthedocs.io/en/stable/tutorial/part_2.html
let socket = null, temporizadorSondeo = null;

function indicar(modo) {
  const chip = $("#conexion");
  const textos = { ws: ["Tiempo real · WebSocket", "chip verde"], sondeo: ["Sondeo cada 1 s", "chip ambar"] };
  [chip.textContent, chip.className] = textos[modo];
}

async function ponerseAlDia() {
  const datos = await pedir(`/api/historico/?despues_de=${ultimoId}&limite=50`);
  datos.eventos.reverse().forEach((ev) => procesarEvento(ev));   // del más antiguo al más nuevo
}

function iniciarSondeo() {
  if (temporizadorSondeo) return;
  indicar("sondeo");
  temporizadorSondeo = setInterval(() => ponerseAlDia().catch(() => {}), 1000);
}

function detenerSondeo() {
  clearInterval(temporizadorSondeo);
  temporizadorSondeo = null;
}

function conectarWebSocket() {
  const protocolo = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocolo}://${location.host}/ws/dashboard/`);
  socket.addEventListener("open", () => {
    detenerSondeo();
    indicar("ws");
    ponerseAlDia().catch(() => {});   // por si llegó algo mientras no había conexión
  });
  socket.addEventListener("message", (m) => {
    const { tipo, datos } = JSON.parse(m.data);
    if (tipo === "evento") procesarEvento(datos);
    else if (tipo === "escenario") mostrarEscenario(datos);
  });
  socket.addEventListener("close", () => {
    iniciarSondeo();
    setTimeout(conectarWebSocket, 5000);
  });
}

// ============================================================ arranque
async function iniciar() {
  GRAFO = await pedir("/api/grafo/");
  crearGraficas();
  dibujarPlano($("#plano"), null);
  prepararSimulador();
  $("#form-historico").addEventListener("submit", (e) => { e.preventDefault(); cargarHistorico(); });
  await cargarEscenarios();
  const datos = await cargarHistorico();
  if (datos.eventos.length) {
    // Se muestra el más reciente sin generar alertas por eventos antiguos.
    // La fila ya está en el histórico, así que no se vuelve a añadir.
    procesarEvento(datos.eventos[0], { alertar: false, alHistorico: false });
  }
  conectarWebSocket();
}

iniciar().catch((err) => agregarAlerta(`Error al iniciar el dashboard: ${err.message}`, "critica"));
