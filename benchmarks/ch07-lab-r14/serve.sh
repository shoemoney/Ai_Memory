docker run -d --name memlab-07-ollama --cpus=8 --memory=4g \
  --label "memlab.owner=$LAB_TOKEN" \
  -p 127.0.0.1:39070:11434 -v /var/tmp/memlab-07:/lab \
  -e OLLAMA_MODELS=/lab/ollama -e OLLAMA_MAX_LOADED_MODELS=1 \
  ollama/ollama:0.40.16
venv/bin/python - <<'PY'
import json, time, urllib.request
for attempt in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:39070/api/version') as r:
            print(json.load(r))
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit('Ollama did not start')
PY
printf 'FROM /lab/stock.gguf\n' > stock.Modelfile
printf 'FROM /lab/edited.gguf\n' > edited.Modelfile
docker exec memlab-07-ollama ollama create stock -f /lab/stock.Modelfile
docker exec memlab-07-ollama ollama create edited -f /lab/edited.Modelfile
docker exec memlab-07-ollama ollama --version
