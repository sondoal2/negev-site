"""GIF 'layer on layer': layers.html with one data source added per frame, fixed camera (headless Edge over DevTools + Pillow).
  python scripts/make_layers_gif.py <site_dir> [he|ar|en]   ->  gifs/<lang>/00-layer-on-layer.gif"""
import sys, os, subprocess, threading, functools, http.server, socketserver, tempfile, json, time, base64, urllib.request, io
import websocket
from PIL import Image
site = os.path.abspath(sys.argv[1]); lang = sys.argv[2] if len(sys.argv) > 2 else 'he'
W, H, N = 1200, 675, 6
exe = next(b for b in [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'] if os.path.exists(b))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp(); dp = 9335
proc = subprocess.Popen([exe, '--headless=new', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars',
                         '--force-device-scale-factor=1', f'--user-data-dir={tmp}', f'--window-size={W},{H}', f'--remote-debugging-port={dp}', 'about:blank'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{dp}/json')); break
        except Exception: time.sleep(.5)
    ws = websocket.create_connection(next(t for t in tabs if t['type'] == 'page')['webSocketDebuggerUrl'], timeout=120); i = [0]
    def call(m, **p):
        i[0] += 1; ws.send(json.dumps({'id': i[0], 'method': m, 'params': p}))
        while True:
            r = json.loads(ws.recv())
            if r.get('id') == i[0]: return r.get('result', {})
    call('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=1, mobile=False)
    call('Page.navigate', url=f'http://127.0.0.1:{port}/layers.html?lang={lang}&step=0')
    t0 = time.time()
    while time.time() - t0 < 120 and call('Runtime.evaluate', expression='document.title')['result'].get('value') != 'READY': time.sleep(1)
    frames = []
    for n in range(N):
        call('Runtime.evaluate', expression=f'window.setStep({n})', awaitPromise=True)
        time.sleep(2.0)
        frames.append(Image.open(io.BytesIO(base64.b64decode(call('Page.captureScreenshot', format='png')['data']))).convert('RGB'))
        print('frame', n, flush=True)
    ws.close()
finally:
    proc.terminate()
out_dir = os.path.join(site, 'gifs', lang); os.makedirs(out_dir, exist_ok=True)
for n, f in enumerate(frames): f.save(os.path.join(tmp, f'layer_{n}.png'))
pal = frames[-1].quantize(colors=180, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
path = os.path.join(out_dir, '00-layer-on-layer.gif')
q[0].save(path, save_all=True, append_images=q[1:], duration=[2200] + [1900] * (N - 2) + [6000], loop=0, optimize=False, disposal=1)
print('wrote', path, os.path.getsize(path) // 1024, 'KB  frames in', tmp)
