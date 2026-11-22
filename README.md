# Micro850 Conveyor Automation

**Allen-Bradley Micro850 · Connected Components Workbench · Ladder · Modbus TCP**

Conveyor sorting station with photoeye sensors, part classification, production counters, reject/diverter logic, emergency stop, automatic sequences and jam detection. The PLC logic is documented ladder-by-ladder and reproduced in a Python simulator with a real Modbus TCP server.

> **Nota (ES):** Proyecto de demostración. La lógica se validó en simulador y sobre Modbus TCP; el proyecto CCW no se descargó a un Micro850 real.

---

## 1. Industrial problem

A conveyor line must detect incoming parts, classify them by size, route rejects to a diverter and keep accurate production counts. It must stop safely on E-stop or jam and expose production data to a supervisory HMI over Modbus TCP.

## 2. Objectives

- Run the conveyor in manual or automatic mode.
- Detect parts with PE1 and classify small/large with PE2.
- Activate the diverter for rejected parts.
- Count total, small, large and rejected parts.
- Detect jams from blocked sensor plus missing encoder pulses.
- Expose all data through a documented Modbus TCP register map.

## 3. Architecture

```text
 PE1/PE2/jam sensors + encoder
             |
      Micro850 (CCW, Ladder)
             |
        Modbus TCP server
             |
     +-------+--------+
     v                v
 Python HMI       Modbus client/tests
 (HTTP bridge)
```

The Python simulator implements the same sequence and register map, so development and tests do not require hardware. See [docs/architecture.md](docs/architecture.md) and [docs/modbus-map.md](docs/modbus-map.md).

## 4. Components

| Layer | Technology |
| --- | --- |
| PLC | Allen-Bradley Micro850, CCW, Ladder Diagram |
| Communication | Modbus TCP (server on PLC, client for supervision) |
| Simulation | Python standard library, Modbus TCP server |
| HMI | Static HTML/JS served by Python HTTP bridge |
| Tests | Python `unittest`, raw Modbus frames, HTTP API |

## 5. Documents

- [Architecture](docs/architecture.md)
- [I/O list](docs/io-list.md)
- [Modbus register map](docs/modbus-map.md)
- [Control sequence](docs/control-sequence.md)
- [Test plan](docs/test-plan.md)
- [Ladder program reference](plc/documentation/ladder-reference.md)

## 6. Screenshots

- [HMI mockup](screenshots/hmi.svg)
- [Conveyor sequence](screenshots/sequence.svg)

## 7. Run

```powershell
cd "C:\Users\Bismarck Acevedo\Documents\Github\micro850-conveyor-automation"
python -m unittest discover -s simulation/tests -v
python simulation/conveyor_server.py
```

Test result: `Ran 26 tests ... OK`.

- HMI: `http://127.0.0.1:4010`
- Modbus TCP: `127.0.0.1:5020`, unit ID 1

CLI demo:

```powershell
python simulation/conveyor_simulator.py --duration 30
```

Modbus read example:

```powershell
python simulation/modbus_client.py --host 127.0.0.1 --port 5020 --start 0 --quantity 8
```

## 8. Evidence matrix

| Item | Status |
| --- | --- |
| Conveyor state machine and counting | Simulated and unit tested |
| Modbus TCP server/client | Tested with raw frames in Python |
| Ladder program | Designed and documented, not downloaded to Micro850 |
| CCW project file | Not provided (proprietary binary) |
| HMI data | Synthetic simulation data |

## 9. Limitations and future work

- No physical Micro850, sensors or diverter were connected.
- Modbus TCP is implemented as a training server; production deployments should use a certified stack.
- Add Ethernet/IP adaptation and OEE dashboards in a later iteration.

## 10. Quality checklist

- [x] Industrial problem clearly defined
- [x] Architecture and communication diagrams
- [x] Organized source code
- [x] Functional control simulation
- [x] User interface
- [x] Documented tests
- [x] Modbus map and register documentation
- [x] Complete README
- [x] Repository initialized on `main`

## 11. Optional real-mode adapter

`MODE=simulation` stays the default; the simulated Modbus TCP server and tests are unchanged. An optional Modbus TCP client (`simulation/real_adapter.py`) is enabled with `MODE=real`, `MODBUS_HOST`, `MODBUS_PORT` and `MODBUS_UNIT_ID`, with configurable register/coil maps. It is read-only unless `ALLOW_WRITES=true` and never falls back silently. See [docs/real-integration.md](docs/real-integration.md) and [config/real.env.example](config/real.env.example).

---

**Author:** Bismarck Acevedo — Electronic Engineer, Industrial Automation & PLC Programming.
