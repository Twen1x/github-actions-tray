import json, time, sys
from pathlib import Path
import psutil
from PySide6.QtCore import QTimer, QThread
from PySide6.QtWidgets import QApplication
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import TrayApplication, _default_config
class Store:
    def load(self):
        return _default_config()
app = QApplication([])
tray = TrayApplication(app, Store())
# Deterministic offline workload: no credentials or remote API dependencies.
tray.poller.poll_once = lambda: time.sleep(0.05)
samples=[]
process=psutil.Process()
start=time.monotonic()
cpu=sum(process.cpu_times()[:2])
timer=QTimer()
def sample():
    samples.append(process.memory_info().rss)
timer.timeout.connect(sample)
timer.start(1000)
tray.start()
def finish():
    elapsed=time.monotonic()-start
    print(json.dumps({'seconds':round(elapsed,2),'cpu_percent_one_core':round(100*(sum(process.cpu_times()[:2])-cpu)/elapsed,3),'rss_peak_mib':round(max(samples)/1024**2,2),'scenario':'native Windows UI, idle, mocked polling (50ms), no credentials'},indent=2))
    tray._quit()
QTimer.singleShot(30000,finish)
app.exec()
assert not tray.poll_thread.isRunning()
