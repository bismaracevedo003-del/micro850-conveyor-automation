# Control sequence

## 1. States

| State | Condition | Outputs |
| --- | --- | --- |
| `STOPPED` (0) | No run command | Motor off, diverter retracted |
| `RUNNING` (1) | Run command and no alarms | Motor on, sorting active |
| `JAM` (2) | Jam timer expired | Motor off, red light on |
| `ESTOP` (3) | E-stop input open | Motor off, alarms latched |

## 2. Sorting sequence

1. PE1 detects a part at the infeed → latch `B_PartDetected`.
2. PE2 reads height at the next zone → `B_PartLarge = 1` for tall parts.
3. A reject flag is assigned from a deterministic pattern (every 5th part) for demonstration.
4. When the part reaches the diverter zone, `Q0.1` pulses for 0.6 s if rejected.
5. At the end of the belt, counters increment and the part record is removed.

## 3. Jam detection

- The encoder must produce pulses while the belt runs.
- If PE1 stays blocked and no pulse is seen for 3 s, `B_JamAlarm` latches and the state changes to `JAM`.
- Reset clears the alarm only when PE1 is clear.

## 4. E-stop

E-stop has the highest priority. It immediately removes the motor run output and latches `B_EStopAlarm`. A reset with the E-stop healthy returns the system to `STOPPED`.

## 5. Throughput

`Throughput_pph = Parts_Total / uptime_hours`, computed from simulated uptime. It is an estimate for demo purposes, not a validated KPI.

## 6. Nota (ES)

La clasificación y el reject se generan artificialmente para demostrar la secuencia; no hay sensores reales conectados.
