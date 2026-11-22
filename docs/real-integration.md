# Real-mode integration (Micro850 conveyor)

## 1. Default behaviour

`MODE` is unset by default, which means `simulation`. The simulated Modbus TCP
server (`simulation/modbus_tcp.py`), HTTP bridge, HMI and all tests are
unchanged. `simulation/real_adapter.py` is an optional **client** returned only
by the new factory; it does not replace or wrap the simulated server.

## 2. Enabling real mode

```powershell
$env:MODE = 'real'
$env:REAL_STRICT = 'true'
$env:MODBUS_HOST = '192.0.2.20'      # documentation IP: replace with the PLC IP
$env:MODBUS_PORT = '502'
$env:MODBUS_UNIT_ID = '1'
```

All three `MODBUS_*` variables are mandatory in real mode; placeholder values
(`<...>`) count as missing. If `pymodbus` is absent, config is incomplete, or
the PLC is unreachable, the adapter raises `RealModeDependencyError`,
`RealModeConfigurationError` or `RealModeError`. It never falls back to
simulation. Optional packages are declared in `requirements-real.txt` and are
not installed or required for the simulation tests.

## 3. Configurable register and coil maps

Defaults match `docs/modbus-map.md` (protocol addresses):

| Tag | Address | Tag | Address |
| --- | --- | --- | --- |
| `State` | 0 | `Sensor_Jam` | 9 |
| `Parts_Total` | 1 | `EStop_OK` | 10 |
| `Parts_Small` | 2 | `Jam_Alarm` | 11 |
| `Parts_Large` | 3 | `Diverter_Active` | 12 |
| `Parts_Rejected` | 4 | `Uptime_s` | 13 |
| `Throughput_pph` | 5 | `Last_Part_Type` | 14 |
| `Belt_Speed_pct` | 6 | `Conveyor_Run` (coil) | 0 |
| `Sensor_PE1` | 7 | `Auto_Mode` (coil) | 4 |
| `Sensor_PE2` | 8 | | |

`MODBUS_REGISTER_MAP` and `MODBUS_COIL_MAP` are optional JSON objects that
override individual addresses, e.g.:

```powershell
$env:MODBUS_REGISTER_MAP = '{"State":100,"Parts_Total":101}'
$env:MODBUS_COIL_MAP = '{"Conveyor_Run":10}'
```

Unknown tags, non-integer addresses or values outside 0-65535 fail with a
clear error. `MODBUS_UNIT_ID` must be 1-247.

## 4. Read-only by default

`ALLOW_WRITES=false` (default): `snapshot()`/`tick()` only read holding
registers and coils, returning the same tag contract as the simulator
(`source` becomes `real-modbus`). `write_coil()`, `write_register()`,
`start()`, `stop()`, `reset()` and `set_speed()` raise `WriteNotAllowedError`
until `ALLOW_WRITES=true` is set explicitly.

E-stop and jam are physical safety inputs. Software commands must never be
used to bypass them.

## 5. Programmatic use

```python
from real_adapter import create_conveyor_source

source = create_conveyor_source()
try:
    print(source.tick())
finally:
    close = getattr(source, 'close', None)
    if close:
        close()
```

## 6. Verification

```powershell
python -m unittest discover -s simulation/tests -v
```
