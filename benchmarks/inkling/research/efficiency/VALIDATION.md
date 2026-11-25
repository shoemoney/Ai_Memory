# Validation, 2026-11-25

- `python3 -m unittest discover -s tests -v`: **13 passed**, offline on the workstation.
- `bash -n energy_run.sh set_mtp.sh`: passed.
- Telemetry instrumentation applied in memory to the complete downloaded pinned
  `batch_generator.py` (SHA-256 checked), and compiled successfully: 220054 bytes.
  No installed source on the Mac Studio was edited.
- Allowed remote probe: macOS 27.2.1 (26B131), ten samples at requested 500 ms,
  actual total 5.441301122 s. All requested samplers worked; CPU/GPU/ANE power,
  combined power and elapsed_ns present. Existing background GPU work observed.
- No model inference or energy benchmark ran. Actual acceptance, energy per answer,
  and speedup remain unmeasured; those still have to be collected per variant.
