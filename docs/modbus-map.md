# Modbus TCP register map

Unit ID: 1. Registers are 16-bit, big-endian, starting at protocol address 0 (documented as 40001).

## Coils (function 01 read / 05 write)

| Coil | Name | Access |
| --- | --- | --- |
| 0 | `Conveyor_Run` | R/W |
| 1 | `Diverter_Extend` | R/W |
| 2 | `Reject_Gate` | R/W |
| 3 | `Reset_Alarms` | W (pulse) |
| 4 | `Auto_Mode` | R/W |

## Holding registers (function 03 read / 06 write)

| Register | Protocol address | Name | Description |
| --- | --- | --- | --- |
| 40001 | 0 | `State` | 0 stopped, 1 running, 2 jam, 3 E-stop |
| 40002 | 1 | `Parts_Total` | Total parts processed |
| 40003 | 2 | `Parts_Small` | Small parts count |
| 40004 | 3 | `Parts_Large` | Large parts count |
| 40005 | 4 | `Parts_Rejected` | Rejected parts count |
| 40006 | 5 | `Throughput_pph` | Parts per hour (estimate) |
| 40007 | 6 | `Belt_Speed_pct` | 0-100 % |
| 40008 | 7 | `Sensor_PE1` | 0/1 |
| 40009 | 8 | `Sensor_PE2` | 0/1 |
| 40010 | 9 | `Sensor_Jam` | 0/1 |
| 40011 | 10 | `EStop_OK` | 0/1 |
| 40012 | 11 | `Jam_Alarm` | 0/1 |
| 40013 | 12 | `Diverter_Active` | 0/1 |
| 40014 | 13 | `Uptime_s` | Running seconds |
| 40015 | 14 | `Last_Part_Type` | 0 none, 1 small, 2 large |

## Example request

Read registers 40001-40008:

```text
00 01 00 00 00 06 01 03 00 00 00 08
```

## Nota (ES)

El mapa está diseñado para que un cliente Modbus cualquiera pueda supervisar la banda sin conocer la marca del PLC.
