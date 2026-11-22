import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from conveyor_simulator import ConveyorSimulator
from modbus_tcp import ModbusServer

HMI_ROOT = Path(__file__).resolve().parent.parent / 'hmi'


class ConveyorApplication:
    def __init__(self, http_port=4010, modbus_port=5020):
        self.simulator = ConveyorSimulator()
        self.modbus = ModbusServer(('127.0.0.1', modbus_port), self.simulator)
        self.http = ThreadingHTTPServer(('127.0.0.1', http_port), ConveyorHandler)
        self.http.app = self
        self.stop_event = threading.Event()
        self.modbus_thread = None
        self.http_thread = None
        self.simulation_thread = None

    @property
    def modbus_port(self):
        return self.modbus.server_address[1]

    @property
    def http_port(self):
        return self.http.server_address[1]

    def start(self):
        self.modbus_thread = threading.Thread(target=self.modbus.serve_forever, daemon=True)
        self.http_thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        for thread in (self.modbus_thread, self.http_thread, self.simulation_thread):
            thread.start()
        return self

    def stop(self):
        self.stop_event.set()
        self.modbus.shutdown()
        self.http.shutdown()
        self.modbus.server_close()
        self.http.server_close()

    def _simulation_loop(self):
        while not self.stop_event.is_set():
            self.simulator.tick(0.2)
            time.sleep(0.2)


class ConveyorHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename):
        path = HMI_ROOT / filename
        if not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'text/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
        }.get(path.suffix, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == '/api/state':
            state = self.server.app.simulator.snapshot()
            state['modbus_port'] = self.server.app.modbus_port
            self._send_json(state)
            return
        if self.path in ('/', '/index.html'):
            self._send_file('index.html')
            return
        if self.path == '/app.js':
            self._send_file('app.js')
            return
        if self.path == '/styles.css':
            self._send_file('styles.css')
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError:
            self._send_json({'error': 'invalid JSON'}, 400)
            return
        simulator = self.server.app.simulator
        if self.path == '/api/command':
            command = str(body.get('command', '')).upper()
            if command == 'START':
                simulator.start()
            elif command == 'STOP':
                simulator.stop()
            elif command == 'RESET':
                simulator.reset()
            else:
                self._send_json({'error': 'unknown command'}, 400)
                return
        elif self.path == '/api/part':
            simulator.inject_part(body.get('type', 'small'))
        elif self.path == '/api/fault':
            active = bool(body.get('active', True))
            fault = body.get('fault')
            if fault == 'jam':
                simulator.inject_jam(active)
            elif fault == 'e_stop':
                simulator.set_estop(active)
            else:
                self._send_json({'error': 'unknown fault'}, 400)
                return
        elif self.path == '/api/speed':
            simulator.set_speed(body.get('speed_pct', 50))
        else:
            self.send_error(404)
            return
        self._send_json(simulator.snapshot())


def main():
    app = ConveyorApplication()
    app.start()
    print(f'Conveyor HMI: http://127.0.0.1:{app.http_port}')
    print(f'Modbus TCP: 127.0.0.1:{app.modbus_port} (unit 1)')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == '__main__':
    main()
