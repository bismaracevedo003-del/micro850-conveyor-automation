import json
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conveyor_server import ConveyorApplication  # noqa: E402
from conveyor_simulator import (  # noqa: E402
    ESTOP,
    JAM,
    RUNNING,
    STOPPED,
    ConveyorSimulator,
    REGISTER_NAMES,
)
from modbus_client import (  # noqa: E402
    read_coils,
    read_holding_registers,
    write_coil,
    write_register,
)
from modbus_tcp import ModbusServer  # noqa: E402


def advance(simulator, seconds, dt=0.2):
    for _ in range(int(round(seconds / dt))):
        simulator.tick(dt)


class ConveyorModelTests(unittest.TestCase):
    def setUp(self):
        self.conveyor = ConveyorSimulator()

    def test_initial_state(self):
        self.assertEqual(self.conveyor.state, STOPPED)
        self.assertEqual(self.conveyor.registers()[0], STOPPED)

    def test_start_sets_running(self):
        self.conveyor.start()
        self.conveyor.tick()
        self.assertEqual(self.conveyor.state, RUNNING)
        self.assertEqual(self.conveyor.snapshot()['Conveyor_Run'], 1)

    def test_stop_sets_stopped(self):
        self.conveyor.start()
        self.conveyor.stop()
        self.conveyor.tick()
        self.assertEqual(self.conveyor.state, STOPPED)

    def test_small_part_is_counted(self):
        self.conveyor.start()
        self.conveyor.inject_part('small')
        advance(self.conveyor, 12)
        state = self.conveyor.snapshot()
        self.assertEqual(state['Parts_Total'], 1)
        self.assertEqual(state['Parts_Small'], 1)
        self.assertEqual(state['Parts_Large'], 0)

    def test_large_part_is_counted(self):
        self.conveyor.start()
        self.conveyor.inject_part('large')
        advance(self.conveyor, 12)
        state = self.conveyor.snapshot()
        self.assertEqual(state['Parts_Large'], 1)
        self.assertEqual(state['Last_Part_Type'], 2)

    def test_fifth_part_is_rejected(self):
        self.conveyor.start()
        self.conveyor.part_sequence = 4
        self.conveyor.inject_part('small')
        advance(self.conveyor, 6)
        state = self.conveyor.snapshot()
        self.assertEqual(state['Parts_Rejected'], 1)

    def test_counters_are_consistent(self):
        self.conveyor.start()
        for kind in ('small', 'small', 'large', 'large'):
            self.conveyor.inject_part(kind)
        advance(self.conveyor, 14)
        state = self.conveyor.snapshot()
        self.assertEqual(state['Parts_Total'], 4)
        self.assertEqual(state['Parts_Small'] + state['Parts_Large'], state['Parts_Total'])

    def test_jam_latches_after_threshold(self):
        self.conveyor.start()
        self.conveyor.inject_jam(True)
        advance(self.conveyor, 3.5)
        state = self.conveyor.snapshot()
        self.assertEqual(state['State'], JAM)
        self.assertEqual(state['Jam_Alarm'], 1)
        self.assertEqual(state['Conveyor_Run'], 0)

    def test_reset_does_not_clear_active_jam(self):
        self.conveyor.inject_jam(True)
        self.conveyor.start()
        advance(self.conveyor, 3.5)
        self.conveyor.reset()
        advance(self.conveyor, 0.5)
        self.assertEqual(self.conveyor.state, JAM)

    def test_reset_clears_cleared_jam(self):
        self.conveyor.inject_jam(True)
        self.conveyor.start()
        advance(self.conveyor, 3.5)
        self.conveyor.inject_jam(False)
        self.conveyor.reset()
        advance(self.conveyor, 0.5)
        self.assertEqual(self.conveyor.state, STOPPED)
        self.assertEqual(self.conveyor.snapshot()['Jam_Alarm'], 0)

    def test_estop_has_priority(self):
        self.conveyor.start()
        self.conveyor.set_estop(True)
        advance(self.conveyor, 0.5)
        state = self.conveyor.snapshot()
        self.assertEqual(state['State'], ESTOP)
        self.assertEqual(state['EStop_OK'], 0)
        self.assertEqual(state['Conveyor_Run'], 0)

    def test_estop_reset_returns_to_stopped(self):
        self.conveyor.set_estop(True)
        self.conveyor.start()
        advance(self.conveyor, 0.5)
        self.conveyor.set_estop(False)
        self.conveyor.reset()
        advance(self.conveyor, 0.5)
        self.assertEqual(self.conveyor.state, STOPPED)

    def test_speed_is_clamped(self):
        self.conveyor.set_speed(150)
        self.assertEqual(self.conveyor.belt_speed_pct, 100)
        self.conveyor.set_speed(-20)
        self.assertEqual(self.conveyor.belt_speed_pct, 0)

    def test_throughput_updates(self):
        self.conveyor.start()
        self.conveyor.inject_part('small')
        advance(self.conveyor, 12)
        self.assertGreater(self.conveyor.snapshot()['Throughput_pph'], 0)

    def test_register_map_has_fifteen_registers(self):
        self.assertEqual(len(self.conveyor.registers()), len(REGISTER_NAMES))

    def test_write_coil_controls_run(self):
        self.assertTrue(self.conveyor.write_coil(0, 1))
        self.conveyor.tick()
        self.assertEqual(self.conveyor.state, RUNNING)
        self.assertTrue(self.conveyor.write_coil(0, 0))
        self.conveyor.tick()
        self.assertEqual(self.conveyor.state, STOPPED)

    def test_write_register_controls_speed(self):
        self.assertTrue(self.conveyor.write_register(6, 75))
        self.assertEqual(self.conveyor.snapshot()['Belt_Speed_pct'], 75)


class ModbusTests(unittest.TestCase):
    def setUp(self):
        self.server = ModbusServer(('127.0.0.1', 0), ConveyorSimulator())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_fc03_reads_holding_registers(self):
        values = read_holding_registers('127.0.0.1', self.port, 0, 8)
        self.assertEqual(len(values), 8)
        self.assertEqual(values[0], STOPPED)
        self.assertEqual(values[6], 50)

    def test_fc05_write_coil_starts_conveyor(self):
        write_coil('127.0.0.1', self.port, 0, True)
        self.assertTrue(self.server.simulator.run_cmd)

    def test_fc06_write_register_sets_speed(self):
        write_register('127.0.0.1', self.port, 6, 80)
        self.assertEqual(self.server.simulator.belt_speed_pct, 80)

    def test_fc01_reads_coils(self):
        coils = read_coils('127.0.0.1', self.port, 0, 5)
        self.assertEqual(len(coils), 5)
        self.assertEqual(coils[4], 1)

    def test_invalid_function_returns_exception(self):
        from modbus_client import exchange

        with self.assertRaises(ValueError):
            exchange('127.0.0.1', self.port, bytes([0x10, 0x00, 0x00, 0x00, 0x01]))

    def test_invalid_register_returns_exception(self):
        with self.assertRaises(ValueError):
            read_holding_registers('127.0.0.1', self.port, 14, 4)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.app = ConveyorApplication(http_port=0, modbus_port=0).start()
        time.sleep(0.4)

    def tearDown(self):
        self.app.stop()

    def get(self, path):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.app.http_port}{path}') as response:
            return response.status, response.read()

    def post(self, path, payload):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.app.http_port}{path}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_hmi_page_is_served(self):
        status, body = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn(b'Conveyor Sorting Station', body)

    def test_api_state(self):
        status, body = self.get('/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['StateName'], 'STOPPED')

    def test_api_command_and_part(self):
        self.post('/api/command', {'command': 'START'})
        time.sleep(0.4)
        state = self.post('/api/part', {'type': 'large'})
        self.assertEqual(state['StateName'], 'RUNNING')


if __name__ == '__main__':
    unittest.main()
