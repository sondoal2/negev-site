"""Export every story of the atlas as its own .gif file (map on the left; topic, one question, the two sides, the gap and the source on the right).

The frames are drawn by gif.html (same data files as the site, same formulas). This script serves the site folder on a local port,
asks headless Edge/Chrome for ONE tall screenshot per GIF (all frames stacked, gif.html?f=all), cuts it into frames and writes the GIF with Pillow.
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
        'sport': ('05-sport-facilities-per-youth', 9), 'sportdist': ('05-sport-facility-1km', 11)}
BROWSERS = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Google\Chrome\Application\chrome.exe']
exe = next(b for b in BROWSERS if os.path.exists(b))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=site)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
out_dir = os.path.join(site, 'gifs', lang); os.makedirs(out_dir, exist_ok=True)
tmp = tempfile.mkdtemp(prefix='offmap_gif_')
try:
    for gid, (name, n) in GIFS.items():
        if only and gid not in only: continue
        shot = os.path.join(tmp, gid + '.png')
        subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1', f'--user-data-dir={os.path.join(tmp, "profile")}',
                        f'--window-size={W},{H * n}', '--virtual-time-budget=20000', f'--screenshot={shot}',
                        f'http://127.0.0.1:{port}/gif.html?g={gid}&lang={lang}&f=all'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        im = Image.open(shot).convert('RGB')
        assert im.size[1] >= H * n, (gid, im.size)
        frames = [im.crop((0, i * H, W, (i + 1) * H)) for i in range(n)]
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
