"""Per-process reserve checks. No existing services are changed."""
import json,os,subprocess,threading,time

def pressure():
    s=subprocess.check_output(['memory_pressure'],text=True)
    free=int(s.split('System-wide memory free percentage: ')[1].split('%')[0])
    p=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True,capture_output=True)
    return free,p.stdout.strip()

def guard():
    while True:
        free,level=pressure()
        if free<=30 or level in ('2','4'):
            print(json.dumps({'event':'pressure_shutdown','free_percent':free,'kernel_level':level}),flush=True)
            os._exit(75)
        time.sleep(5)

def admit():
    free,level=pressure()
    assert free>=40 and level not in ('2','4'),'Memory admission refused'
    print(json.dumps({'event':'admitted','free_percent':free,'kernel_level':level}),flush=True)
    threading.Thread(target=guard,daemon=True).start()
    return free
