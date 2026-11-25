#!/usr/bin/env python3
"""Run unmodified oMLX CLI and retain true process/MLX memory high-water marks."""
import json,resource,time,os,signal
from pathlib import Path
import mlx.core as mx
from omlx.cli import main
started=time.time()
def finish_signal(signum,frame):
 raise SystemExit(0)
# Uvicorn restores and re-raises captured signals after graceful shutdown.
# Raising SystemExit in our original handler lets the finally block retain peaks.
signal.signal(signal.SIGTERM,finish_signal)
signal.signal(signal.SIGINT,finish_signal)
try:
 main()
finally:
 (Path(os.environ['INKLING_LAB_ROOT'])/'server-memory.json').write_text(json.dumps({
  'started_unix':started,'stopped_unix':time.time(),
  'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'mlx_peak_allocated_bytes':mx.get_peak_memory(),
  'platform':'Darwin (ru_maxrss is bytes)',
 },indent=2))
