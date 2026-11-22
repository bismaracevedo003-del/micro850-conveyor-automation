# Ladder program reference

CCW project files are proprietary binaries, so the versioned source of truth is this rung-by-rung description plus the Python simulator that implements the same behavior.

## PRG_IO_MAP

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `XIC I0.0 OTE B_PE1` | PE1 input to internal bit |
| 1 | `XIC I0.1 OTE B_PE2` | Height sensor to internal bit |
| 2 | `XIC I0.2 OTE B_JamSensor` | Jam sensor to internal bit |
| 3 | `XIO I0.4 OTL B_EStopAlarm` | Latch E-stop on open contact |

## PRG_CONVEYOR

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `XIO I0.4 OTE B_EStopAlarm` | E-stop alarm logic |
| 1 | `TON B_JamTimer 3000 ms` | Jam timer when PE1 blocked and no encoder pulse |
| 2 | `OTL B_JamAlarm` | Latch jam when timer done |
| 3 | `XIC B_RunCmd XIO B_EStopAlarm XIO B_JamAlarm OTE Q0.0` | Motor run output |
| 4 | `XIC Q0.0 OTE Q0.3` | Green stack light |

## PRG_SORT

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `ONS B_PE1 OTL B_PartDetected` | Detect new part |
| 1 | `XIC B_PartDetected XIC B_PE2 OTL B_PartLarge` | Classify large |
| 2 | `XIC B_PartDetected XIO B_PE2 OTL B_PartSmall` | Classify small |
| 3 | `XIC B_PartAtDiverter XIC B_PartReject TON 600 ms` | Diverter pulse timer |
| 4 | `XIC B_DiverterTimer OTE Q0.1` | Diverter output |

## PRG_COUNTERS

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `CTU C_Total` | Increment total at end of belt |
| 1 | `CTU C_Small` if small | Increment small counter |
| 2 | `CTU C_Large` if large | Increment large counter |
| 3 | `CTU C_Rejected` if reject | Increment reject counter |

## PRG_MODBUS

| Rung | Instruction | Description |
| --- | --- | --- |
| 0 | `MOV State -> HR40001` | State telemetry |
| 1 | `MOV counters -> HR40002..40005` | Production counters |
| 2 | `MOV sensors -> HR40008..40012` | Sensor and alarm status |
| 3 | `MOV speed setpoint -> HR40007` | HMI speed reference |

## Nota (ES)

Los nombres `XIC`, `XIO`, `OTE`, `OTL` y `TON` son la notación estándar de Ladder; cada rung tiene su equivalente en `simulation/conveyor_simulator.py`.
