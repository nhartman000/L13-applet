const $ = id => document.getElementById(id);
const pretty = x => { try { return JSON.stringify(typeof x==='string'?JSON.parse(x):x, null, 2) } catch { return String(x) } };

function samplePayload(){
  return {
    seed: { problem: "Hypercube mapping", goal: "stable projection" },
    params: { epsilon: 0.1, tau: 0.05, p: 2, R: 2.0, sigma: 0.0, max_iter: 256 },
    anchors: [{ name: "physics_consistency", target: [1,0,0] }],
    state_vecs: { physics_consistency: [1,0,0] }
  };
}

function loadSettings(){ $('url').value = localStorage.getItem('l13_url') || '/kernel/run';
  $('payload').value = localStorage.getItem('l13_payload') || JSON.stringify(samplePayload(), null, 2); }
function saveSettings(){ localStorage.setItem('l13_url', $('url').value.trim());
  localStorage.setItem('l13_payload', $('payload').value); }

$('presetSample').onclick = ()=> $('payload').value = JSON.stringify(samplePayload(), null, 2);
$('presetEmpty').onclick = ()=> $('payload').value = pretty({seed:{},params:{},anchors:[],state_vecs:{}});
$('saveBtn').onclick = saveSettings;

let mode = 'auto';
$('vizMode').onchange = (e)=>{ mode = e.target.value; pickControls(); }

function pickControls(){
  const use = (mode==='auto'? lastAttractor : mode);
  $('juliaControls').style.display = (use==='julia') ? 'flex' : 'none';
  $('bulbControls').style.display  = (use==='mandelbulb') ? 'flex' : 'none';
}

let lastAttractor = 'julia';
let vizState = { julia:{c:[0,0],zoom:1.2}, bulb:{orbit:0.8,zoom:1.0} };

$('cre').oninput = ()=>{}; $('cim').oninput = ()=>{}; $('zoom').oninput = ()=>{};
$('orbit').oninput = ()=>{}; $('bzoom').oninput = ()=>{};

$('runBtn').onclick = runL13;

async function runL13(){
  const url = $('url').value.trim();
  let body; try { body = JSON.parse($('payload').value) } catch(e){ alert('Invalid JSON: '+e.message); return; }
  $('resp').textContent = 'Sending…';
  try{
    const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const txt = await r.text(); $('resp').textContent = pretty(txt);
    const data = JSON.parse(txt);
    renderDecision(data);
    renderTimeline(data.history||[]);
    const viz = data.viz || {};
    lastAttractor = viz.attractor || 'julia';
    if (viz.julia && viz.julia.c){ $('cre').value = (+viz.julia.c[0]).toFixed(3); $('cim').value = (+viz.julia.c[1]).toFixed(3); }
    pickControls();
  }catch(e){ $('resp').textContent = 'Network error: '+e.message; }
}

function renderDecision(data){
  const el = $('decision'); el.textContent = data.decision || '—';
  el.classList.remove('ok','warn','bad');
  if (!data.decision) return;
  if (data.decision.includes('converged')) el.classList.add('ok');
  else if (data.decision.includes('bounded')) el.classList.add('warn');
  else el.classList.add('bad');
  const hist = data.history||[];
  const lastFinite = [...hist].reverse().find(h => h.pass_id !== '∞');
  const lastDelta = lastFinite?.delta ?? null;
  const lastR = lastFinite?.dsvm_r ?? null;
  $('deltaVal').textContent = lastDelta==null ? '—' : lastDelta.toFixed(3);
  $('rVal').textContent = lastR==null ? '—' : lastR.toFixed(3);
  const inf = hist.find(h => h.pass_id==='∞');
  $('infVal').textContent = inf ? `${inf.outcome} @ ${inf.iters}` : '—';
}

function renderTimeline(history){
  const t = $('timeline'); t.innerHTML=''; const finite = history.filter(h => h.pass_id !== '∞');
  const maxDelta = Math.max(0.001, ...finite.map(h => (h.delta??0)));
  finite.forEach(h => { const bar = document.createElement('div'); bar.className='bar';
    bar.style.height = (10 + 100 * (h.delta||0)/maxDelta) + 'px';
    bar.title = `k=${h.pass_id}  Δ=${(h.delta??0).toFixed(3)}  r=${h.dsvm_r??'—'}`;
    const k = document.createElement('div'); k.className='k'; k.textContent = h.pass_id; bar.appendChild(k); t.appendChild(bar); });
}

const canvas = document.getElementById('viz');
const gl = canvas.getContext('webgl');
if (!gl) console.warn('WebGL not available');

const vsSrc = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}';
function compile(type, src){ const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
function link(vs, fs){ const pr = gl.createProgram(); gl.attachShader(pr, vs); gl.attachShader(pr, fs); gl.linkProgram(pr); return pr; }

const fsJulia = `
precision highp float;
uniform vec2 u_res, u_c;
uniform float u_zoom;
const int MAX_IT = 180;
void main(){
  vec2 uv = (gl_FragCoord.xy - 0.5*u_res) / (min(u_res.x,u_res.y)*0.5) / u_zoom;
  float zx=uv.x, zy=uv.y;
  int i; for(i=0;i<MAX_IT;i++){ float x2=zx*zx - zy*zy + u_c.x; float y2=2.0*zx*zy + u_c.y; zx=x2; zy=y2; if(zx*zx+zy*zy>4.0) break; }
  float t = float(i)/float(MAX_IT);
  vec3 col = mix(vec3(0.02,0.08,0.2), vec3(0.1,0.8,1.0), pow(t,0.6));
  gl_FragColor = vec4(col,1.0);
}`;

const fsBulb = `
precision highp float;
uniform vec2 u_res;
uniform float u_orbit, u_zoom;
const int MAX_STEPS=96; const float FAR=20.0; const float EPS=0.001; const float BAIL=8.0; const float POWER=8.0;

float deMandelbulb(vec3 p){
  vec3 z=p; float dr=1.0; float r=0.0;
  for (int i=0;i<32;i++){
    r = length(z); if (r>BAIL) break;
    float theta = acos(z.z/r); float phi = atan(z.y, z.x);
    float zr = pow(r, POWER); dr = pow(r, POWER-1.0)*POWER*dr + 1.0;
    float st = sin(POWER*theta), ct = cos(POWER*theta);
    float sp = sin(POWER*phi),   cp = cos(POWER*phi);
    z = zr * vec3(st*cp, st*sp, ct) + p;
  }
  return 0.5*log(r)*r/dr;
}

vec3 normal(vec3 p){
  float e=0.002;
  vec2 h=vec2(1,-1)*0.5773;
  return normalize(h.xyy*deMandelbulb(p+h.xyy*e)+h.yyx*deMandelbulb(p+h.yyx*e)+h.yxy*deMandelbulb(p+h.yxy*e)+h.xxx*deMandelbulb(p+h.xxx*e));
}

void main(){
  vec2 uv = (gl_FragCoord.xy/u_res)*2.0-1.0; uv.x *= u_res.x/u_res.y;
  float ang = u_orbit;
  vec3 ro = vec3(3.0*u_zoom*cos(ang), 2.0*u_zoom, 3.0*u_zoom*sin(ang));
  vec3 ta = vec3(0.0, 0.0, 0.0);
  vec3 ww = normalize(ta - ro);
  vec3 uu = normalize(cross(vec3(0.0,1.0,0.0), ww));
  vec3 vv = cross(ww, uu);
  vec3 rd = normalize(uv.x*uu + uv.y*vv + 1.8*ww);

  float t=0.0; int i;
  for(i=0;i<MAX_STEPS;i++){
    vec3 p = ro + rd*t;
    float d = deMandelbulb(p);
    if (d<EPS || t>FAR) break;
    t += d*0.8;
  }
  if (t>FAR){ gl_FragColor = vec4(0.02,0.05,0.12,1.0); return; }
  vec3 p = ro + rd*t;
  vec3 n = normal(p);
  vec3 light = normalize(vec3(0.8,0.9,0.5));
  float diff = clamp(dot(n, light), 0.0, 1.0);
  vec3 col = mix(vec3(0.1,0.2,0.35), vec3(0.1,0.8,1.0), diff);
  gl_FragColor = vec4(col,1.0);
}`;

const quad = new Float32Array([-1,-1, 1,-1, -1,1, 1,1]);
const buf = gl && gl.createBuffer(); if (gl){ gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, quad, gl.STATIC_DRAW); }

let progJulia, progBulb, aLocJulia, aLocBulb, uJulia={}, uBulb={};

function makeProgram(fs){
  const vs = compile(gl.VERTEX_SHADER, vsSrc);
  const fsCompiled = compile(gl.FRAGMENT_SHADER, fs);
  const pr = link(vs, fsCompiled);
  const loc = gl.getAttribLocation(pr, 'p');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  return {pr, loc};
}

function initGL(){
  if(!gl) return;
  { const m = makeProgram(fsJulia); progJulia = m.pr; aLocJulia = m.loc;
    uJulia.res = gl.getUniformLocation(progJulia, 'u_res');
    uJulia.c   = gl.getUniformLocation(progJulia, 'u_c');
    uJulia.zoom= gl.getUniformLocation(progJulia, 'u_zoom');
  }
  { const m = makeProgram(fsBulb); progBulb = m.pr; aLocBulb = m.loc;
    uBulb.res   = gl.getUniformLocation(progBulb, 'u_res');
    uBulb.orbit = gl.getUniformLocation(progBulb, 'u_orbit');
    uBulb.zoom  = gl.getUniformLocation(progBulb, 'u_zoom');
  }
}

function render(){
  if(!gl) return requestAnimationFrame(render);
  const use = (mode==='auto'? lastAttractor : mode);
  gl.viewport(0,0,canvas.width, canvas.height);
  if (use === 'mandelbulb'){
    $('juliaControls').style.display='none'; $('bulbControls').style.display='flex';
    gl.useProgram(progBulb);
    gl.uniform2f(uBulb.res, canvas.width, canvas.height);
    gl.uniform1f(uBulb.orbit, parseFloat($('orbit').value || '0.8'));
    gl.uniform1f(uBulb.zoom,  parseFloat($('bzoom').value || '1.0'));
  } else {
    $('juliaControls').style.display='flex'; $('bulbControls').style.display='none';
    gl.useProgram(progJulia);
    gl.uniform2f(uJulia.res, canvas.width, canvas.height);
    gl.uniform2f(uJulia.c, parseFloat($('cre').value||'0.0'), parseFloat($('cim').value||'0.0'));
    gl.uniform1f(uJulia.zoom, parseFloat($('zoom').value||'1.0'));
  }
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  requestAnimationFrame(render);
}

function start(){ loadSettings(); initGL(); render(); }
start();
