#!/usr/bin/env bash
# Configure hook for accept.py. Never run while another lab job holds the Mac Studio.
set -euo pipefail
: "${INKLING_MTP_MODE:?on or off}"
: "${INKLING_MODEL:?model id}"
: "${MODEL_DIR:?absolute the Mac Studio checkpoint path}"
[[ "$INKLING_MTP_MODE" =~ ^(on|off)$ ]] || exit 2
[[ "$INKLING_MODEL" =~ ^[A-Za-z0-9_.+-]+$ ]] || exit 2
[[ "${MODEL_DIR##*/}" == "$INKLING_MODEL" ]] || { echo 'MODEL_DIR basename must equal model id' >&2; exit 2; }
here=$(cd -- "$(dirname -- "$0")" && pwd)
infra=$(cd "$here/../../infra" && pwd)
timeout 65 "$infra/serve.sh" "$MODEL_DIR" stop
timeout 20 ssh -o BatchMode=yes <lan-address> python3 - "$INKLING_MODEL" "$INKLING_MTP_MODE" <<'PY'
import json, pathlib, sys
model, mode = sys.argv[1:]
p = pathlib.Path.home() / 'inkling-lab/omlx-data/model_settings.json'
original = p.read_bytes() if p.exists() else b'{"version":1,"models":{}}'
doc = json.loads(original)
row = doc.setdefault('models', {}).setdefault(model, {})
if row.get('dflash_enabled') or row.get('vlm_mtp_enabled'):
    raise SystemExit('Disable competing decoder settings explicitly before study')
backup = p.with_name('model_settings.pre-efficiency.json')
if not backup.exists(): backup.write_bytes(original)
row['mtp_enabled'] = mode == 'on'
q = p.with_suffix('.efficiency.tmp')
q.write_text(json.dumps(doc, indent=2) + '\n')
q.replace(p)
PY
timeout 30 "$infra/serve.sh" "$MODEL_DIR" start
