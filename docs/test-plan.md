# Test plan and results

## 1. Scope

Tests cover the conveyor state machine, classification, counters, diverter timing, jam detection, E-stop, Modbus frames and the register map. No physical Micro850 was connected.

## 2. Cases

| ID | Case | Expected | Status |
| --- | --- | --- | --- |
| T-01 | Start command | State RUNNING, motor on | Pass |
| T-02 | Stop command | State STOPPED, motor off | Pass |
| T-03 | Small part processed | `Parts_Small` increases | Pass |
| T-04 | Large part processed | `Parts_Large` increases | Pass |
| T-05 | Rejected part | `Parts_Rejected` increases, diverter pulses | Pass |
| T-06 | Total counter consistency | Total = small + large | Pass |
| T-07 | Jam after 3 s blocked | State JAM, motor off | Pass |
| T-08 | Reset with jam active | Jam remains | Pass |
| T-09 | Reset after jam clears | State STOPPED | Pass |
| T-10 | E-stop | State ESTOP, motor off | Pass |
| T-11 | Encoder pulses | Uptime and throughput update | Pass |
| T-12 | Modbus FC03 read | Holding registers returned big-endian | Pass |
| T-13 | Modbus FC05 write coil | Run coil changes state | Pass |
| T-14 | Modbus FC06 write register | Speed setpoint accepted | Pass |
| T-15 | Modbus exception | Invalid function returns exception | Pass |

## 3. Command

```powershell
python -m unittest discover -s simulation/tests -v
```

## 4. Pending hardware verification

- Download CCW project to Micro850.
- Wire and test PE1/PE2, encoder and E-stop.
- Verify Modbus TCP client in the real HMI/SCADA.

## 5. Ejecución real

```text
Ran 26 tests in 6.331s
OK
```

The 26 tests cover model behavior, Modbus FC01/FC03/FC05/FC06, exceptions, HTTP HMI and API endpoints.

## 6. Nota (ES)

Los casos T-01 a T-15 y sus variantes están automatizados; el hardware queda como trabajo futuro explícito.
