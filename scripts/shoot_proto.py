"""Render story.html scenes to JPG with headless Edge over the DevTools protocol (no window).
Waits until the page sets document.title = 'READY' (map idle after the scene's layers load), then captures.
  python scripts/shoot_proto.py <site_dir> <out_dir> [01,07]"""
import sys, os, subprocess, threading, functools, http.server, socketserver, tempfile, json, time, base64, urllib.request, io
import websocket
from PIL import Image

site = os.path.abspath(sys.argv[1]); out = os.path.abspath(sys.argv[2]); os.makedirs(out, exist_ok=True)
only = sys.argv[3].split(',') if len(sys.argv) > 3 else ['01', '02', '03', '04', '05', '06', '07']
W, H = 1600, 900
BROWSERS = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']
exe = next(b for b in BROWSERS if os.path.exists(b))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=site)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp(prefix='offmap_proto_')
dbg_port = 9333
proc = subprocess.Popen([exe, '--headless=new', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars',
                         '--force-device-scale-factor=1', f'--user-data-dir={os.path.join(tmp, "profile")}', f'--window-size={W},{H}',
                         f'--remote-debugging-port={dbg_port}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tabs = []
    for _ in range(60):
        try:
            tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{dbg_port}/json')); break
        except Exception:
            time.sleep(.5)
    page = next(t for t in tabs if t.get('type') == 'page')
    ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=120)
    mid = [0]
    def call(method, **params):
        mid[0] += 1; ws.send(json.dumps({'id': mid[0], 'method': method, 'params': params}))
        while True:
            m = json.loads(ws.recv())
            if m.get('id') == mid[0]: return m.get('result', {})
    call('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=1, mobile=False)
    lang = os.environ.get('TOUR_LANG', 'ar')
    for s in only:
        call('Page.navigate', url=f'http://127.0.0.1:{port}/story.html?s={s}&lang={lang}')
        t0 = time.time(); ready = False
        while time.time() - t0 < 90:
            r = call('Runtime.evaluate', expression='document.title')
            if r.get('result', {}).get('value') == 'READY': ready = True; break
            time.sleep(1)
        time.sleep(2.5)  # let the last tiles paint
        img = call('Page.captureScreenshot', format='png')
        Image.open(io.BytesIO(base64.b64decode(img['data']))).convert('RGB').save(os.path.join(out, f'proto_{s}.jpg'), quality=86)
        print('ok' if ready else 'TIMEOUT', s, round(time.time() - t0, 1), 's')
    ws.close()
finally:
    proc.terminate()
