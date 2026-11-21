"""Export every story of the atlas as its own .gif file (map on the left; topic, one question, the two sides, the gap and the source on the right).

The frames are drawn by gif.html (same data files as the site, same formulas). This script serves the site folder on a local port,
asks headless Edge over the DevTools protocol for one screenshot per frame (gif.html?f=<i>) and writes the GIF with Pillow.
No browser window opens.

  python scripts/make_gifs.py <site_dir> [lang=ar] [only=bus,school]
Output: gifs/<lang>/<nn>-<name>.gif   (1200 x 675)
"""
import sys, os, subprocess, threading, functools, http.server, socketserver, tempfile, shutil
from PIL import Image

site = os.path.abspath(sys.argv[1]); lang = sys.argv[2] if len(sys.argv) > 2 else 'ar'
only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
W, H = 1200, 675
# id -> (file name, number of frames drawn by gif.html)
GIFS = {'homes': ('01-homes-off-the-map', 11), 'localities': ('02-new-localities-since-1948', 15), 'industry': ('03-industrial-land', 10), 'arnona': ('03-business-tax', 9),
        'bus': ('04-bus-stop-walking-distance', 11), 'school': ('05-elementary-school-1km', 11), 'bagrut': ('05-bagrut-university', 11),
        'sport': ('05-sport-facilities-per-youth', 9), 'sportdist': ('05-sport-facility-1km', 11),
        'parks': ('05b-parks-paper-vs-ground', 11), 'police': ('06-police-station-2km', 11), 'lethal': ('06-lethal-violence', 9), 'noplan': ('07-no-approved-plan', 11)}
BROWSERS = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Google\Chrome\Application\chrome.exe']
exe = next(b for b in BROWSERS if os.path.exists(b))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=site)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
out_dir = os.path.join(site, 'gifs', lang); os.makedirs(out_dir, exist_ok=True)
tmp = tempfile.mkdtemp(prefix='offmap_gif_')
import json, time, base64, io, urllib.request, websocket
_n = [0]
def shoot(urls, w, h):
    """one fresh headless Edge per GIF (a second navigation in the same browser came back black)"""
    _n[0] += 1
    with socketserver.TCPServer(('127.0.0.1', 0), None) as t: dbg = t.server_address[1]  # a free port, never a leftover browser's
    proc = subprocess.Popen([exe, '--headless=new', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', '--force-device-scale-factor=1',
                             f'--user-data-dir={os.path.join(tmp, "profile%d" % _n[0])}', f'--remote-debugging-port={dbg}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try: tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{dbg}/json')); break
            except Exception: time.sleep(.5)
        ws = websocket.create_connection(next(t for t in tabs if t.get('type') == 'page')['webSocketDebuggerUrl'], timeout=180); mid = [0]
        def call(method, **params):
            mid[0] += 1; ws.send(json.dumps({'id': mid[0], 'method': method, 'params': params}))
            while True:
                m = json.loads(ws.recv())
                if m.get('id') == mid[0]: return m.get('result', {})
        call('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=1, mobile=False)
        out = []
        for url in urls:  # one frame per page load, at the normal 1200x675 viewport
            call('Runtime.evaluate', expression="document.title=''")
            call('Page.navigate', url=url); t0 = time.time(); title = ''
            while time.time() - t0 < 120:
                title = str(call('Runtime.evaluate', expression='document.title').get('result', {}).get('value', ''))
                if title.startswith('ready'): break
                time.sleep(.4)
            if not title.startswith('ready'): print('  page never became ready:', url, repr(title))
            time.sleep(.6)
            img = call('Page.captureScreenshot', format='png')
            out.append(Image.open(io.BytesIO(base64.b64decode(img['data']))).convert('RGB'))
        ws.close()
        return out
    finally:
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # the whole Edge tree
try:
    for gid, (name, n) in GIFS.items():
        if only and gid not in only: continue
        frames = shoot([f'http://127.0.0.1:{port}/gif.html?g={gid}&lang={lang}&f={i}' for i in range(n)], W, H)
        frames[-1].save(os.path.join(tmp, f'{gid}_last.png')); frames[0].save(os.path.join(tmp, f'{gid}_first.png')); frames[n // 2].save(os.path.join(tmp, f'{gid}_mid.png'))
        # one shared palette taken from the last frame (it holds every colour, including the red gap)
        pal = frames[-1].quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
        dur = [1500] + [420] * (n - 2) + [4500]
        path = os.path.join(out_dir, name + '.gif')
        q[0].save(path, save_all=True, append_images=q[1:], duration=dur, loop=0, optimize=False, disposal=1)
        print(f'{name}.gif  {n} frames  {os.path.getsize(path) / 1024:.0f} KB')
    keep = os.environ.get('GIF_KEEP')
    if keep:
        os.makedirs(keep, exist_ok=True)
        for f in os.listdir(tmp):
            if f.endswith('.png'): shutil.copy(os.path.join(tmp, f), keep)
finally:
    srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
