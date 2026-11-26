const { app, BrowserWindow } = require('electron');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { URL } = require('url');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
};

function sendJson(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(body);
}

function readRequestBody(req, limit = 32 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', chunk => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error('Import request is too large. Select a smaller HDL project.'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch { reject(new Error('Import request was not valid JSON.')); }
    });
    req.on('error', reject);
  });
}

function findPython() {
  for (const candidate of process.platform === 'win32' ? ['python', 'python3'] : ['python3', 'python']) {
    const result = spawnSync(candidate, ['--version'], { encoding: 'utf8' });
    if (!result.error && result.status === 0) return candidate;
  }
  throw new Error('Python was not found. Install Python and make it available in PATH.');
}

function importHdl(payload) {
  const files = Array.isArray(payload.files) ? payload.files : [];
  if (!files.length) throw new Error('Choose at least one Verilog/SystemVerilog or VHDL file.');
  const language = payload.language === 'vhdl' ? 'vhdl' : 'verilog';
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kianv-import-'));
  try {
    const paths = files.map((file, index) => {
      const original = String(file.name || `source_${index}`);
      const safe = path.basename(original).replace(/[^A-Za-z0-9_.-]/g, '_') || `source_${index}`;
      const target = path.join(temp, `${String(index).padStart(3, '0')}_${safe}`);
      fs.writeFileSync(target, String(file.content || ''), 'utf8');
      return target;
    });
    const python = findPython();
    const unpackedViewer = path.join(process.resourcesPath, 'app.asar.unpacked', 'tools', 'module_viewer.py');
    const viewer = fs.existsSync(unpackedViewer) ? unpackedViewer : path.join(root, 'tools', 'module_viewer.py');
    const languageArgs = language === 'vhdl' ? ['--vhdl'] : [];
    const list = spawnSync(python, [viewer, ...languageArgs, ...paths, '--list-modules'], {
      cwd: root, encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
    });
    if (list.status !== 0) throw new Error((list.stderr || list.stdout || 'The HDL project could not be parsed.').trim());
    const tops = [];
    const modules = [];
    let section = '';
    for (const line of `${list.stdout}\n`.split(/\r?\n/)) {
      if (line.startsWith('Inferred top-level candidates:')) { section = 'tops'; continue; }
      if (line.startsWith('Parsed modules:')) { section = 'modules'; continue; }
      const match = line.match(/^\s{2}(.+?)(?: \[top candidate\])?$/);
      if (!match) continue;
      if (section === 'tops') tops.push(match[1]);
      if (section === 'modules') modules.push(match[1].replace(/ \[top candidate\]$/, ''));
    }
    const selected = payload.module || tops[0] || modules[0];
    if (!selected) throw new Error('No HDL modules/entities were found.');
    const output = path.join(temp, 'rendered');
    const render = spawnSync(python, [viewer, ...languageArgs, ...paths, '--module', selected, '--output', output], {
      cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
    });
    if (render.status !== 0) throw new Error((render.stderr || render.stdout || `Could not render module ${selected}.`).trim());
    const jsonFile = fs.readdirSync(output).find(name => name.endsWith('.json') && !name.endsWith('.meta.json'));
    if (!jsonFile) throw new Error('The module viewer did not produce a structural JSON netlist.');
    return {
      key: 'imported',
      label: `Imported ${language.toUpperCase()} project · ${selected}`,
      source: files.map(file => file.name).join(', '),
      language,
      module: selected,
      modules,
      tops,
      raw: JSON.parse(fs.readFileSync(path.join(output, jsonFile), 'utf8')),
    };
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

function createLocalServer() {
  const server = http.createServer(async (req, res) => {
    try {
      const requestPath = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
      if (req.method === 'POST' && requestPath === '/api/import') {
        try { sendJson(res, 200, importHdl(await readRequestBody(req))); }
        catch (error) { sendJson(res, 422, { error: error.message }); }
        return;
      }
      const relative = requestPath === '/' ? '/dist/index.html' : (/^\/(data|transistor)(\/|$)/.test(requestPath) ? `/dist${requestPath}` : requestPath);
      const filePath = path.resolve(root, `.${relative.startsWith('/') ? relative : `/${relative}`}`);
      if (!filePath.startsWith(root + path.sep) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Not found');
        return;
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    } catch (error) {
      if (!res.headersSent) { res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' }); res.end(error.message); }
    }
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function createWindow() {
  const server = await createLocalServer();
  const address = server.address();
  const win = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1000,
    minHeight: 700,
    backgroundColor: '#071018',
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  win.on('closed', () => server.close());
  await win.loadURL(`http://127.0.0.1:${address.port}/`);
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
