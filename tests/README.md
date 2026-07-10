# Tests

Tests de simulación (sin hardware). Reemplazan `fastboot` por un mock que
responde como un dispositivo real, así se puede ejercitar el flujo completo sin
un teléfono conectado.

```bash
python tests/test_unlock_sim.py
```

- `test_unlock_sim.py` — simula el desbloqueo del bootloader (Mi A1 / tissot):
  desbloqueo normal, fallback a `oem unlock`, y caso sin dispositivo.

Solo usa la librería estándar (sin `pytest`). Sale con código `0` si todo pasa.
