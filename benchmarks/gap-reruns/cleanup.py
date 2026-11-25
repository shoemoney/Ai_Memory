#!/usr/bin/env python3
"""Stops everything this task started, removes what it created on the dev host and the model host, and writes
results/cleanup.json with before/after evidence. Run once at the end: python3 cleanup.py [--before results/before.json]."""
import json, os, subprocess, sys, time

MODEL_HOST = os.environ["MODEL_HOST"]  # ssh name of the model host
SCRATCH = "/data/scratch/membench/gap-reruns"
TMP = "/var/tmp/membench-gap-reruns"
HERE = os.path.dirname(os.path.abspath(__file__))

def sh(cmd, host=None, timeout=120):
    if host: cmd = ["ssh", "-o", "ConnectTimeout=10", host, cmd if isinstance(cmd, str) else " ".join(cmd)]
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

def snapshot():
    s = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    s["dev_df"] = sh("df -h /data/scratch /var/tmp /")
    s["dev_free"] = sh("free -m | sed -n 2p")
    s["dev_containers"] = sh("docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' | grep -i membench || true")
    s["dev_images_hindsight"] = sh("docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -i hindsight || true")
    s["dev_listeners_39980_39999"] = sh("ss -ltnp 2>/dev/null | grep -E ':399[89][0-9]' || true")
    s["dev_task_processes"] = sh("ps -eo pid,args | grep -E 'membench-gap-reruns|g10-beam-light|g44-sleep-time|run_decider|drive.py' | grep -v grep | grep -v cleanup.py || true")
    s["dev_scratch_du"] = sh(f"du -sh {SCRATCH} {TMP} 2>/dev/null || true")
    m = "ls -d ~/membench-gap-reruns-tmp* 2>/dev/null; du -sh ~/membench-gap-reruns-tmp 2>/dev/null; df -h ~ | tail -1; memory_pressure -Q | tail -1; ps -axo pid,rss,args | grep -E 'llama-server|embed_server|run_decider|membench-gap-reruns' | grep -v grep || true; lsof -nP -iTCP:39980-39999 -sTCP:LISTEN 2>/dev/null | tail -n +2 || true"
    s["model_host"] = sh(m, MODEL_HOST)
    return s

if "--before" in sys.argv:
    json.dump(snapshot(), open(sys.argv[sys.argv.index("--before") + 1], "w"), indent=1); sys.exit()

before = json.load(open(os.path.join(HERE, "results", "before.json"))) if os.path.exists(os.path.join(HERE, "results", "before.json")) else snapshot()
actions = []
def act(desc, cmd, host=None):
    actions.append({"action": desc, "output": sh(cmd, host)})

act("remove task container", "docker rm -f membench-gap-reruns-hindsight 2>&1 || true")
act("remove Hindsight image pulled for this task", "docker rmi ghcr.io/vectorize-io/hindsight:1.2.3 2>&1 || true")
act("stop ssh tunnels to the model host (ports 39980-39999)", "for p in $(ps -eo pid,args | awk '/ssh -N .*-L .*3998/ && !/awk/ {print $1}'); do kill $p; done; echo done")
act("stop task processes on dev host", "for p in $(ps -eo pid,args | awk '/(run_decider|drive.py|sleeptime.py|run_beam.py)/ && !/awk/ && !/cleanup.py/ {print $1}'); do kill $p; done; echo done")
act("stop model-host servers (llama-server, embedding server, decision-model server, watchdog): only processes with files open under the task folder",
    "lsof +D ~/membench-gap-reruns-tmp -t 2>/dev/null | sort -u | xargs kill 2>/dev/null; sleep 8; echo done", MODEL_HOST)
act("remove model-host scratch (models, venvs, caches, logs)", "rm -rf ~/membench-gap-reruns-tmp; echo removed", MODEL_HOST)
act("remove dev scratch", f"rm -rf {SCRATCH} {TMP}; rmdir /data/scratch/membench 2>/dev/null; echo removed")
after = snapshot()
json.dump({"before": before, "actions": actions, "after": after}, open(os.path.join(HERE, "results", "cleanup.json"), "w"), indent=1)
print(json.dumps(after, indent=1))
