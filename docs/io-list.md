# I/O list

## Micro850 physical I/O

| Address | Type | Description | State |
| --- | --- | --- | --- |
| `I0.0` | DI | PE1 infeed photoeye | 1 = part present |
| `I0.1` | DI | PE2 height sensor | 1 = large part |
| `I0.2` | DI | Jam photoeye | 1 = obstructed |
| `I0.3` | DI | Encoder pulse | 1 = pulse |
| `I0.4` | DI | Emergency stop (NC) | 1 = healthy |
| `I0.5` | DI | Auto mode selector | 1 = auto |
| `I0.6` | DI | Reset pushbutton | 1 = pressed |
| `Q0.0` | DO | Conveyor motor run | 1 = run |
| `Q0.1` | DO | Diverter actuator | 1 = extend |
| `Q0.2` | DO | Reject gate | 1 = open |
| `Q0.3` | DO | Green stack light | 1 = run |
| `Q0.4` | DO | Red stack light | 1 = fault |

## Internal bits

| Bit | Description |
| --- | --- |
| `B_AutoMode` | Automatic sequence enabled |
| `B_RunCmd` | Conveyor run command |
| `B_PartDetected` | PE1 rising edge latch |
| `B_PartLarge` | Classification result |
| `B_PartReject` | Reject flag for current part |
| `B_DiverterTimer` | Diverter pulse in progress |
| `B_JamAlarm` | Jam latched |
| `B_EStopAlarm` | E-stop latched |

## Nota (ES)

Los sensores se leen como 1 = activo; el E-stop es NC para detectar también corte de cable.
