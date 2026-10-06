// ---------- CNC / laser export + machine sending (added on top of the original 2D drafting tool) ----------
// PATCH: replace everything in drafting.js from the line
//   "// ---------- CNC / laser export + machine sending ..."
// to the end of the file with this section.
// Requires /static/ung-auth.js to be loaded BEFORE drafting.js (see drafting_cnc_panel.html);
// it adds the dashboard token to API calls and the bridge pairing token to bridge calls.
// Uses the global `shapes` array defined at the top of drafting.js.
// RECONSTRUCTED: the PDF lost this section's line breaks; the whole section is rewritten cleanly here.

const BRIDGE_URL = (window.UNG && window.UNG.BRIDGE_URL) || 'http://127.0.0.1:8765';
let lastCncDownload = null;
let lastCncStats = null;
let cncPollTimer = null;

function cncEl(id) {
  return document.getElementById(id);
}

function cncNum(id, fallback) {
  const v = parseFloat(cncEl(id).value);
  return Number.isFinite(v) ? v : fallback;
}

function cncSettings() {
  const cutDepth = cncNum('cnc-depth-pass', 1);
  return {
    mode: cncEl('cnc-mode').value,
    scale_mm_per_px: cncNum('cnc-scale', 1),
    feed_rate: cncNum('cnc-feed', 800),
    plunge_rate: 200,
    safe_z: cncNum('cnc-safez', 5),
    cut_depth_per_pass: cutDepth,
    total_depth: cncNum('cnc-total-depth', cutDepth),
    spindle_speed: Math.round(cncNum('cnc-spindle', 12000)),
    laser_power_percent: cncNum('cnc-power', 80),
    max_s: Math.round(cncNum('cnc-max-s', 1000))
  };
}

function cncUpdateModeFields() {
  const laser = cncEl('cnc-mode').value === 'laser';
  document.querySelectorAll('.cnc-only').forEach(el => { el.style.display = laser ? 'none' : ''; });
  document.querySelectorAll('.laser-only').forEach(el => { el.style.display = laser ? '' : 'none'; });
}

function cncBridge(path, init) {
  if (!window.UNG || !window.UNG.bridgeFetch) {
    return Promise.reject(new Error('ung-auth.js is not loaded on this page'));
  }
  return window.UNG.bridgeFetch(path, init);
}

async function bridgeHealth() {
  const r = await fetch(BRIDGE_URL + '/health', { cache: 'no-store' });
  if (!r.ok) {
    throw new Error('Bridge HTTP ' + r.status);
  }
  return await r.json();
}

cncEl('cnc-mode').addEventListener('change', cncUpdateModeFields);
cncUpdateModeFields();

cncEl('cnc-generate').onclick = async () => {
  const status = cncEl('cnc-status');
  const drawingName = cncEl('drawing-name').value || 'drawing';
  if (!shapes.length) {
    status.textContent = 'Nothing to export — draw something first.';
    return;
  }
  status.textContent = 'Generating G-code…';
  try {
    const r = await fetch('/api/manufacturing/cnc-slice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shapes, drawing_name: drawingName, settings: cncSettings() })
    });
    const j = await r.json();
    if (!r.ok) {
      throw new Error(typeof j.detail === 'string' ? j.detail : 'G-code generation failed');
    }
    lastCncDownload = j.download;
    lastCncStats = j.stats;
    cncEl('cnc-send').disabled = false;
    status.textContent = 'G-CODE READY — ' + j.stats.paths + ' cut path(s), ~' + j.stats.estimated_seconds +
      's estimated. Work origin: bottom-left corner of the drawing.\n';
    const a = document.createElement('a');
    a.href = j.download;
    a.download = j.machine_file;
    a.textContent = 'Download G-code';
    a.style.color = '#59d6e7';
    status.appendChild(a);
  } catch (e) {
    status.textContent = 'FAILED — ' + e.message;
  }
};

cncEl('cnc-refresh-ports').onclick = async () => {
  const status = cncEl('cnc-send-status');
  const sel = cncEl('cnc-port');
  status.textContent = 'Checking local bridge for USB ports…';
  try {
    await bridgeHealth();
    const r = await cncBridge('/serial/ports');
    const j = await r.json();
    if (!r.ok || j.error) {
      throw new Error(j.error || ('Bridge HTTP ' + r.status));
    }
    sel.innerHTML = '';
    if (!j.ports.length) {
      sel.innerHTML = '<option value="">No USB devices found</option>';
      status.textContent = 'No serial devices detected — check the machine is plugged in and powered on.';
      return;
    }
    j.ports.forEach(p => {
      const o = document.createElement('option');
      o.value = p.device;
      o.textContent = p.device + ' — ' + p.description;
      sel.appendChild(o);
    });
    status.textContent = 'Found ' + j.ports.length + ' port(s).';
  } catch (e) {
    status.textContent = 'Bridge not reachable — download and run the local bridge first (' + e.message + ')';
  }
};

function cncShowJob(job) {
  const status = cncEl('cnc-send-status');
  if (!job) {
    status.textContent = 'No job on the bridge.';
    return;
  }
  const pct = Math.round((job.progress || 0) * 100);
  let text = 'JOB ' + job.state.toUpperCase() + ' — ' + job.sent_lines + '/' + job.total_lines + ' lines (' + pct + '%)';
  if (job.error) {
    text += ' — ' + job.error;
  }
  status.textContent = text;
}

function cncStopPolling() {
  if (cncPollTimer) {
    clearInterval(cncPollTimer);
    cncPollTimer = null;
  }
}

function cncStartPolling(jobId) {
  cncStopPolling();
  cncPollTimer = setInterval(async () => {
    try {
      const r = await cncBridge('/serial/status?job_id=' + encodeURIComponent(jobId));
      const j = await r.json();
      if (!r.ok || j.error) {
        throw new Error(j.error || ('Bridge HTTP ' + r.status));
      }
      cncShowJob(j.job);
      if (!j.job || !j.job.active) {
        cncStopPolling();
        cncEl('cnc-send').disabled = false;
      }
    } catch (e) {
      cncEl('cnc-send-status').textContent = 'Lost contact with the bridge — ' + e.message;
      cncStopPolling();
      cncEl('cnc-send').disabled = false;
    }
  }, 1000);
}

cncEl('cnc-send').onclick = async () => {
  const status = cncEl('cnc-send-status');
  const port = cncEl('cnc-port').value;
  const baud = cncEl('cnc-baud').value || '115200';
  const mode = cncEl('cnc-mode').value;
  if (!lastCncDownload) {
    status.textContent = 'Generate G-code first.';
    return;
  }
  if (!port) {
    status.textContent = 'Select a USB port first (Refresh USB ports).';
    return;
  }
  const what = mode === 'laser' ? 'LASER' : 'CNC SPINDLE';
  const ok = window.confirm(
    'Send this job to the machine on ' + port + '?\n\n' +
    'This will start the ' + what + ' and move the machine.\n' +
    '• Work zero (X0 Y0) must be at the BOTTOM-LEFT corner of the drawing.\n' +
    '• Clear the work area, wear eye protection, keep the E-stop within reach.\n' +
    (lastCncStats ? '• ' + lastCncStats.paths + ' path(s), about ' + lastCncStats.estimated_seconds + ' s.\n' : '')
  );
  if (!ok) {
    status.textContent = 'Cancelled.';
    return;
  }
  status.textContent = 'Sending G-code to the bridge…';
  cncEl('cnc-send').disabled = true;
  try {
    const gcode = await (await fetch(lastCncDownload)).text();
    const r = await cncBridge('/serial/send', {
      method: 'POST',
      headers: { 'X-Port': port, 'X-Baud': baud, 'X-Machine-Mode': mode },
      body: gcode
    });
    const j = await r.json();
    if (!r.ok || j.error) {
      throw new Error(j.error || 'Machine rejected job');
    }
    status.textContent = 'JOB STARTED — ' + j.total_lines + ' G-code lines queued.';
    cncStartPolling(j.job_id);
  } catch (e) {
    status.textContent = 'SEND FAILED — ' + e.message;
    cncEl('cnc-send').disabled = false;
  }
};

cncEl('cnc-stop').onclick = async () => {
  const status = cncEl('cnc-send-status');
  status.textContent = 'STOPPING…';
  try {
    const port = cncEl('cnc-port').value;
    const baud = cncEl('cnc-baud').value || '115200';
    const headers = { 'X-Baud': baud };
    if (port) {
      headers['X-Port'] = port;
    }
    const r = await cncBridge('/serial/stop', { method: 'POST', headers });
    const j = await r.json();
    if (!r.ok || j.error) {
      throw new Error(j.error || ('Bridge HTTP ' + r.status));
    }
    status.textContent = j.stopped ? 'STOPPED (feed hold + reset + M5 sent).' : 'Nothing to stop: ' + (j.reason || '');
    cncStopPolling();
    cncEl('cnc-send').disabled = false;
  } catch (e) {
    status.textContent = 'STOP FAILED — ' + e.message + ' — use the machine E-stop!';
  }
};

cncEl('cnc-bridge-token').onclick = () => {
  if (window.UNG) {
    window.UNG.bridgeToken(true);
  }
};
