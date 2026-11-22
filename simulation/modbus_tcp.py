import socketserver
import struct

from conveyor_simulator import ConveyorSimulator


def read_exact(connection, count):
    data = b''
    while len(data) < count:
        chunk = connection.recv(count - len(data))
        if not chunk:
            raise ConnectionError('Connection closed')
        data += chunk
    return data


class ModbusHandler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            try:
                header = read_exact(self.request, 7)
                transaction, protocol, length, unit = struct.unpack('>HHHB', header)
                pdu = read_exact(self.request, length - 1)
            except (ConnectionError, OSError):
                return
            if protocol != 0:
                return
            response = self.server.dispatch(unit, pdu)
            if response is None:
                continue
            frame = struct.pack('>HHHB', transaction, 0, 1 + len(response), unit) + response
            try:
                self.request.sendall(frame)
            except OSError:
                return


class ModbusServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address=('127.0.0.1', 5020), simulator=None):
        self.simulator = simulator or ConveyorSimulator()
        super().__init__(address, ModbusHandler)

    def dispatch(self, unit, pdu):
        if unit != 1:
            return bytes([pdu[0] | 0x80, 0x01])
        function = pdu[0]
        data = pdu[1:]
        if function == 0x01:
            return self._read_coils(data)
        if function == 0x03:
            return self._read_registers(data)
        if function == 0x05:
            return self._write_coil(data)
        if function == 0x06:
            return self._write_register(data)
        return bytes([function | 0x80, 0x01])

    def _read_coils(self, data):
        start, quantity = struct.unpack('>HH', data)
        coils = self.simulator.coils()
        if start + quantity > len(coils):
            return bytes([0x81, 0x02])
        packed = bytearray((quantity + 7) // 8)
        for index in range(quantity):
            if coils[start + index]:
                packed[index // 8] |= 1 << (index % 8)
        return bytes([0x01, len(packed)]) + bytes(packed)

    def _read_registers(self, data):
        start, quantity = struct.unpack('>HH', data)
        registers = self.simulator.registers()
        if start + quantity > len(registers):
            return bytes([0x83, 0x02])
        values = registers[start:start + quantity]
        return bytes([0x03, quantity * 2]) + struct.pack('>' + 'H' * quantity, *values)

    def _write_coil(self, data):
        address, value = struct.unpack('>HH', data)
        if not self.simulator.write_coil(address, int(value == 0xFF00)):
            return bytes([0x85, 0x02])
        return bytes([0x05]) + data

    def _write_register(self, data):
        address, value = struct.unpack('>HH', data)
        if not self.simulator.write_register(address, value):
            return bytes([0x86, 0x02])
        return bytes([0x06]) + data
