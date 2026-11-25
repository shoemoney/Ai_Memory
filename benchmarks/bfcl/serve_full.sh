set -euo pipefail
mkdir -p ~/membench-bfcl-tmp
cd ~/membench-bfcl-tmp
minimum_free=${ADMISSION_MIN_FREE:-40}
level=$(sysctl -n kern.memorystatus_vm_pressure_level)
free_percent=$(memory_pressure -Q | awk '/System-wide memory free percentage/ {gsub(/%/, "", $NF);print $NF}')
if [ "$level" != 1 ] || [ "$free_percent" -lt "$minimum_free" ]; then echo 'WAIT_MEMORY'; exit 75; fi
uid=$(id -u)
launchctl bootout gui/$uid/com.membench.bfcl.server 2>/dev/null || true
launchctl bootout gui/$uid/com.membench.bfcl.guard 2>/dev/null || true
if lsof -b -nP -iTCP:39730 -sTCP:LISTEN >/dev/null; then echo 'PORT_OCCUPIED';exit 76;fi
if [ ! -f model.gguf ] || [ "$(shasum -a 256 model.gguf | awk '{print $1}')" != "$MODEL_SHA" ];then
 curl -fL --retry 2 "$MODEL_URL" -o model.gguf.part 2>download.log
 printf '%s  %s\n' "$MODEL_SHA" model.gguf.part | shasum -a 256 -c -
 mv model.gguf.part model.gguf
fi
# Admission is checked again after the download, immediately before loading.
level=$(sysctl -n kern.memorystatus_vm_pressure_level)
free_percent=$(memory_pressure -Q | awk '/System-wide memory free percentage/ {gsub(/%/, "", $NF);print $NF}')
if [ "$level" != 1 ] || [ "$free_percent" -lt "$minimum_free" ]; then echo 'WAIT_MEMORY'; exit 75; fi
slots=4
if [ "$free_percent" -lt 65 ];then slots=2;fi
if [ "$free_percent" -lt 50 ];then slots=1;fi
context=$((slots * 65536))
cat >launch-server.sh <<EOF
#!/bin/bash
cd "$PWD"
echo \$\$ >server.pid
exec /opt/homebrew/bin/llama-server -m model.gguf --host localhost --port 39730 --alias "$MODEL_ALIAS" -c "$context" -np "$slots" -b 512 -ub 128 -ngl 99 --jinja --reasoning-format deepseek --cache-ram 1024 --no-webui
EOF
cat >guard.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
while true;do
 level=$(sysctl -n kern.memorystatus_vm_pressure_level)
 free_percent=$(memory_pressure -Q | awk '/System-wide memory free percentage/ {gsub(/%/, "", $NF);print $NF}')
 printf '%s free=%s pressure=%s\n' "$(date -u +%FT%TZ)" "$free_percent" "$level" >>pressure.log
 if [ "$level" != 1 ];then
  if [ -f server.pid ];then
   pid=$(cat server.pid)
   if ps -p "$pid" -o args= | grep -q 'membench-bfcl-';then kill "$pid" 2>/dev/null || true;fi
  fi
 fi
 sleep 5
done
EOF
for which in server guard;do
 script=launch-server.sh
 keep=false
 if [ "$which" = guard ];then script=guard.sh;keep=true;fi
 cat >"$which.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.membench.bfcl.$which</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>$PWD/$script</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><$keep/>
<key>StandardOutPath</key><string>$PWD/$which.log</string>
<key>StandardErrorPath</key><string>$PWD/$which.log</string>
</dict></plist>
EOF
 launchctl bootstrap gui/$uid "$PWD/$which.plist"
done
echo "SERVING slots=$slots"
