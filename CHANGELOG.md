# Changelog

## 1.0.3

- Deliver polling completion to a QObject slot on the GUI thread.
- Wait asynchronously for polling and token-check threads during shutdown.
- Space automatic polls after completion and coalesce manual refresh requests.
- Keep polling other workflows after malformed API responses.
- Avoid rendering unchanged tray icons and remove the idle 200 ms timer.
- Skip fullscreen inspection when the overlay is disabled.

### Measurement

Windows 10, Python 3.14, native UI, 30.01 seconds, mocked polling with
50 ms latency: CPU 0.052% of one logical core; peak sampled RSS 71.20 MiB.
This is an idle smoke measurement, not a real-network or long-duration benchmark.
Reproduce with `python build/benchmark.py` (requires psutil).
