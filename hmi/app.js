const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return response.json();
}

function render(state) {
  $('state').textContent = state.StateName;
  $('state').className = `state state-${state.State}`;
  $('total').textContent = state.Parts_Total;
  $('small').textContent = state.Parts_Small;
  $('large').textContent = state.Parts_Large;
  $('rejected').textContent = state.Parts_Rejected;
  $('throughput').textContent = `${state.Throughput_pph} pph`;
  $('speed').textContent = `${state.Belt_Speed_pct} %`;
  $('pe1').textContent = `PE1 ${state.Sensor_PE1}`;
  $('pe2').textContent = `PE2 ${state.Sensor_PE2}`;
  $('jamSensor').textContent = `JAM ${state.Sensor_Jam}`;
  $('estop').textContent = state.EStop_OK ? 'E-STOP OK' : 'E-STOP ACTIVE';
  $('estop').className = state.EStop_OK ? '' : 'alarm';
  $('modbusInfo').textContent = `Unit 1 · port ${state.modbus_port} · ${state.Auto_Mode ? 'Auto' : 'Manual'}`;
}

async function refresh() {
  render(await api('/api/state'));
}

async function command(name) {
  render(await api('/api/command', { method: 'POST', body: { command: name } }));
}

async function part(type) {
  render(await api('/api/part', { method: 'POST', body: { type } }));
}

async function fault(name) {
  const current = await api('/api/state');
  const active = name === 'jam' ? !current.Sensor_Jam : !current.EStop_OK;
  render(await api('/api/fault', { method: 'POST', body: { fault: name, active } }));
}

$('start').onclick = () => command('START');
$('stop').onclick = () => command('STOP');
$('reset').onclick = () => command('RESET');
$('addSmall').onclick = () => part('small');
$('addLarge').onclick = () => part('large');
$('injectJam').onclick = () => fault('jam');
$('injectEstop').onclick = () => fault('e_stop');
$('speedInput').oninput = async (event) => {
  render(await api('/api/speed', { method: 'POST', body: { speed_pct: Number(event.target.value) } }));
};

refresh();
setInterval(refresh, 500);
