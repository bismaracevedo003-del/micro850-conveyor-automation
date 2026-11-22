"""Conveyor sorting simulator with the same register map as the Micro850."""

from __future__ import annotations

import argparse
import json
from typing import Any

STOPPED = 0
RUNNING = 1
JAM = 2
ESTOP = 3

STATE_NAMES = {STOPPED: 'STOPPED', RUNNING: 'RUNNING', JAM: 'JAM', ESTOP: 'ESTOP'}

REGISTER_NAMES = (
    'State',
    'Parts_Total',
    'Parts_Small',
    'Parts_Large',
    'Parts_Rejected',
    'Throughput_pph',
    'Belt_Speed_pct',
    'Sensor_PE1',
    'Sensor_PE2',
    'Sensor_Jam',
    'EStop_OK',
    'Jam_Alarm',
    'Diverter_Active',
    'Uptime_s',
    'Last_Part_Type',
)

COIL_NAMES = ('Conveyor_Run', 'Diverter_Extend', 'Reject_Gate', 'Reset_Alarms', 'Auto_Mode')


class ConveyorSimulator:
    def __init__(self, jam_threshold_s: float = 3.0, diverter_pulse_s: float = 0.6):
        self.jam_threshold_s = jam_threshold_s
        self.diverter_pulse_s = diverter_pulse_s
        self.state = STOPPED
        self.run_cmd = False
        self.auto_mode = True
        self.belt_speed_pct = 50.0
        self.e_stop_ok = True
        self.jam_injected = False
        self.parts: list[dict[str, Any]] = []
        self.part_sequence = 0
        self.counters = {'total': 0, 'small': 0, 'large': 0, 'rejected': 0}
        self.diverter_timer_s = 0.0
        self.jam_timer_s = 0.0
        self.uptime_s = 0.0
        self.reset_requested = False
        self.encoder_pulses = 0
        self.last_part_type = 0
        self.elapsed_s = 0.0

    def start(self) -> None:
        self.run_cmd = True
        self.reset_requested = False

    def stop(self) -> None:
        self.run_cmd = False

    def reset(self) -> None:
        self.reset_requested = True

    def set_estop(self, active: bool) -> None:
        self.e_stop_ok = not active

    def inject_jam(self, active: bool) -> None:
        self.jam_injected = active

    def set_speed(self, percent: float) -> None:
        self.belt_speed_pct = min(100.0, max(0.0, float(percent)))

    def inject_part(self, part_type: str = 'small') -> int:
        kind = 'large' if part_type == 'large' else 'small'
        self.part_sequence += 1
        part = {
            'id': self.part_sequence,
            'type': kind,
            'position': 0.0,
            'reject': self.part_sequence % 5 == 0,
            'detected': False,
            'classified': False,
            'diverted': False,
        }
        self.parts.append(part)
        return part['id']

    def tick(self, dt: float = 0.2) -> dict[str, Any]:
        dt = max(0.0, float(dt))
        self.elapsed_s += dt
        self._update_alarms(dt)
        self._update_state()
        self._update_motion(dt)
        self._update_sensors(dt)
        self._update_parts(dt)
        return self.snapshot()

    def _update_alarms(self, dt: float) -> None:
        if self.reset_requested:
            if self.jam_injected is False and not self._pe1_blocked():
                self.jam_timer_s = 0.0
            if self.e_stop_ok:
                self.run_cmd = False
                self.state = STOPPED
            self.reset_requested = False
        if self.jam_injected or self._pe1_blocked():
            self.jam_timer_s += dt
        else:
            self.jam_timer_s = 0.0

    def _update_state(self) -> None:
        if not self.e_stop_ok:
            self.state = ESTOP
            return
        if self.jam_timer_s >= self.jam_threshold_s:
            self.state = JAM
            return
        if self.run_cmd:
            self.state = RUNNING
        else:
            self.state = STOPPED

    def _update_motion(self, dt: float) -> None:
        if self.state != RUNNING:
            return
        if self.jam_injected:
            return
        speed = self.belt_speed_pct * dt * 0.2
        for part in self.parts:
            part['position'] = min(100.0, part['position'] + speed)
        self.uptime_s += dt
        self.encoder_pulses += 1

    def _update_sensors(self, dt: float) -> None:
        if self.diverter_timer_s > 0:
            self.diverter_timer_s = max(0.0, self.diverter_timer_s - dt)

    def _update_parts(self, dt: float) -> None:
        for part in list(self.parts):
            position = part['position']
            if not part['detected'] and 8 <= position <= 12:
                part['detected'] = True
            if not part['classified'] and 22 <= position <= 28:
                part['classified'] = True
                self.last_part_type = 2 if part['type'] == 'large' else 1
            if part['reject'] and not part['diverted'] and position >= 55:
                part['diverted'] = True
                self.diverter_timer_s = self.diverter_pulse_s
                self.counters['rejected'] += 1
            if position >= 100:
                self.counters['total'] += 1
                self.counters[part['type']] += 1
                self.parts.remove(part)

    def _pe1_blocked(self) -> bool:
        return any(8 <= part['position'] <= 12 for part in self.parts)

    def snapshot(self) -> dict[str, Any]:
        state = self.state
        throughput = 0.0
        if self.uptime_s > 0:
            throughput = self.counters['total'] / (self.uptime_s / 3600.0)
        return {
            'State': state,
            'StateName': STATE_NAMES.get(state, 'UNKNOWN'),
            'Parts_Total': self.counters['total'],
            'Parts_Small': self.counters['small'],
            'Parts_Large': self.counters['large'],
            'Parts_Rejected': self.counters['rejected'],
            'Throughput_pph': round(throughput, 1),
            'Belt_Speed_pct': self.belt_speed_pct,
            'Sensor_PE1': int(self._pe1_blocked()),
            'Sensor_PE2': int(any(part['type'] == 'large' and 22 <= part['position'] <= 28 for part in self.parts)),
            'Sensor_Jam': int(self.jam_injected or self.jam_timer_s > 0),
            'EStop_OK': int(self.e_stop_ok),
            'Jam_Alarm': int(self.jam_timer_s >= self.jam_threshold_s),
            'Diverter_Active': int(self.diverter_timer_s > 0),
            'Uptime_s': round(self.uptime_s, 1),
            'Last_Part_Type': self.last_part_type,
            'Conveyor_Run': int(state == RUNNING),
            'Auto_Mode': int(self.auto_mode),
            'source': 'simulator',
            'elapsed_s': round(self.elapsed_s, 1),
        }

    def registers(self) -> list[int]:
        snapshot = self.snapshot()
        values = []
        for name in REGISTER_NAMES:
            value = snapshot[name]
            if name in ('Belt_Speed_pct', 'Throughput_pph'):
                value = round(value)
            values.append(int(value) & 0xFFFF)
        return values

    def coils(self) -> list[int]:
        snapshot = self.snapshot()
        return [
            int(snapshot['Conveyor_Run']),
            snapshot['Diverter_Active'],
            int(snapshot['Parts_Rejected'] > 0),
            0,
            snapshot['Auto_Mode'],
        ]

    def write_coil(self, address: int, value: int) -> bool:
        if address == 0:
            if value:
                self.start()
            else:
                self.stop()
            return True
        if address == 3 and value:
            self.reset()
            return True
        if address == 4:
            self.auto_mode = bool(value)
            return True
        return False

    def write_register(self, address: int, value: int) -> bool:
        if address == 6:
            self.set_speed(value)
            return True
        if address == 14:
            self.last_part_type = value
            return True
        return False


def run_demo(duration_s: int, interval: int) -> None:
    conveyor = ConveyorSimulator()
    conveyor.start()
    for second in range(1, duration_s + 1):
        if second % 3 == 0:
            conveyor.inject_part('large' if second % 6 == 0 else 'small')
        snapshot = conveyor.tick(1.0)
        if second % interval == 0 or second == 1:
            print(json.dumps(snapshot, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description='Simulate a sorting conveyor')
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--interval', type=int, default=2)
    args = parser.parse_args()
    run_demo(args.duration, args.interval)


if __name__ == '__main__':
    main()
