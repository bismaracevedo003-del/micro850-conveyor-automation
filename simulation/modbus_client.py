import argparse
import socket
import struct

TRANSACTION = 1
UNIT = 1


def exchange(host, port, pdu, unit=UNIT):
    with socket.create_connection((host, port), timeout=5) as connection:
        frame = struct.pack('>HHHB', TRANSACTION, 0, 1 + len(pdu), unit) + pdu
        connection.sendall(frame)
        header = b''
        while len(header) < 7:
            chunk = connection.recv(7 - len(header))
            if not chunk:
                raise ConnectionError('Connection closed')
            header += chunk
        _, protocol, length, _ = struct.unpack('>HHHB', header)
        body = b''
        while len(body) < length - 1:
            chunk = connection.recv(length - 1 - len(body))
            if not chunk:
                raise ConnectionError('Connection closed')
            body += chunk
    if body[0] & 0x80:
        raise ValueError(f'Modbus exception {body[0]:#x} code {body[1]}')
    return body


def read_holding_registers(host, port, start, quantity, unit=UNIT):
    response = exchange(host, port, struct.pack('>BHH', 0x03, start, quantity), unit)
    count = response[1]
    values = struct.unpack('>' + 'H' * (count // 2), response[2:2 + count])
    return list(values)


def read_coils(host, port, start, quantity, unit=UNIT):
    response = exchange(host, port, struct.pack('>BHH', 0x01, start, quantity), unit)
    packed = response[2:]
    return [(packed[index // 8] >> (index % 8)) & 1 for index in range(quantity)]


def write_coil(host, port, address, value, unit=UNIT):
    exchange(host, port, struct.pack('>BHH', 0x05, address, 0xFF00 if value else 0), unit)


def write_register(host, port, address, value, unit=UNIT):
    exchange(host, port, struct.pack('>BHH', 0x06, address, value), unit)


def main():
    parser = argparse.ArgumentParser(description='Read Modbus holding registers')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5020)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--quantity', type=int, default=8)
    args = parser.parse_args()
    print(read_holding_registers(args.host, args.port, args.start, args.quantity))


if __name__ == '__main__':
    main()
