# Tests

Tests de simulación (sin hardware). Reemplazan `fastboot` por un mock que
responde como un dispositivo real, así se puede ejercitar el flujo completo sin
un teléfono conectado.

```bash
python tests/test_unlock_sim.py
```

- `test_unlock_sim.py` — 9 escenarios sobre las operaciones críticas:
  - **unlock**: normal, fallback a `oem unlock`, sin dispositivo.
  - **wipe**: normal (`fastboot -w`), fallback a `erase userdata/cache`, sin dispositivo.
  - **flash**: carpeta con `flash_all.bat`, carpeta inexistente, carpeta sin script.
  - **watch**: el vigilante abre la GUI solo en el flanco de conexión (no en cada sondeo).

Solo usa la librería estándar (sin `pytest`). Sale con código `0` si todo pasa.
