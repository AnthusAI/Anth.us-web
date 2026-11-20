"""poll.py LOGFILE [SECONDS] -- every 3 s GET the key pages of anth.us (no redirects followed), log status; stops when the file STOP exists next to the log."""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
PAGES = ["/", "/about/", "/articles/", "/engage/", "/ai-solutions/", "/platform/", "/articles/agent-skills/", "/articles/page/2/", "/ryan/", "/sitemap-index.xml", "/sitemap-0.xml", "/robots.txt", "/404.html", "/css/site-theme.css", "/blog/agent-skills/", "/about", "/tags/ai/"]
EXPECT = {"/blog/agent-skills/": 301, "/about": 301}
class NR(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
op = urllib.request.build_opener(NR)
def get(path):
    try:
        r = op.open(urllib.request.Request("https://anth.us" + path, headers={"User-Agent": "papyrus-poll/1"}), timeout=15)
        code = r.status; r.read()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = "client-error: " + type(e).__name__ + " " + str(e)[:60]
    return path, code
log = Path(sys.argv[1]); stop = log.with_suffix(".stop")
end = time.time() + (float(sys.argv[2]) if len(sys.argv) > 2 else 6 * 3600)
bad = 0; n = 0
with log.open("a") as f, ThreadPoolExecutor(8) as pool:
    while time.time() < end and not stop.exists():
        t = time.time()
        res = list(pool.map(get, PAGES))
        n += 1
        fails = {p: c for p, c in res if c != EXPECT.get(p, 200)}
        bad += len(fails)
        f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "fails": fails}) + "\n"); f.flush()
        time.sleep(max(0, 3 - (time.time() - t)))
    f.write(json.dumps({"summary": {"rounds": n, "unexpected": bad}}) + "\n")
