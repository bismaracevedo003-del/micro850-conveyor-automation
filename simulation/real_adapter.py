"""Optional real-mode (Modbus TCP) source for the conveyor station.

The simulated Modbus TCP server in ``modbus_tcp.py`` is not modified. This
module is an optional client that reads the same documented register map from
a real Micro850. MODE=real is required; missing config or dependencies raise
an error instead of falling back to simulation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

DEFAULT_REGISTER_MAP = {
    'State': 0,
    'Parts_Total': 1,
    'Parts_Small': 2,
    'Parts_Large': 3,
    'Parts_Rejected': 4,
    'Throughput_pph': 5,
    'Belt_Speed_pct': 6,
    'Sensor_PE1': 7,
    'Sensor_PE2': 8,
    'Sensor_Jam': 9,
    'EStop_OK': 10,
    'Jam_Alarm': 11,
    'Diverter_Active': 12,
    'Uptime_s': 13,
    'Last_Part_Type': 14,
}

DEFAULT_COIL_MAP = {
    'Conveyor_Run': 0,
    'Diverter_Extend': 1,
    'Reject_Gate': 2,
    'Reset_Alarms': 3,
    'Auto_Mode': 4,
}

_TRUE_VALUES = ('1', 'true', 'yes', 'on')
_FALSE_VALUES = ('0', 'false', 'no', 'off')


class RealModeError(RuntimeError):
    """Base error for the optional real-mode adapter."""


class RealModeConfigurationError(RealModeError):
    """Raised when MODE=real is requested with incomplete or invalid config."""


class RealModeDependencyError(RealModeError):
    """Raised when MODE=real is requested but its optional package is absent."""


class WriteNotAllowedError(RealModeError):
    """Raised when a write is attempted without ALLOW_WRITES=true."""


@dataclass(frozen=True)
class RealConfig:
    mode: str
    strict: bool
    allow_writes: bool
    log_level: str
    host: str
    port: int
    unit_id: int
    register_map: dict[str, int]
    coil_map: dict[str, int]


def _filled(value: Any) -> bool:
    text = '' if value is None else str(value).strip()
    return bool(text) and not text.startswith('<')


def _env_bool(env: Any, name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    text = str(raw).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise RealModeConfigurationError(f'{name} must be true or false, got {raw!r}')


def _env_int(env: Any, name: str, default: int, minimum: int, maximum: int) -> int:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise RealModeConfigurationError(f'{name} must be an integer, got {raw!r}') from exc
    if not minimum <= value <= maximum:
        raise RealModeConfigurationError(f'{name} must be between {minimum} and {maximum}, got {value}')
    return value


def _load_address_map(env: Any, name: str, defaults: dict[str, int]) -> dict[str, int]:
    result = dict(defaults)
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return result
    try:
        overrides = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise RealModeConfigurationError(f'{name} must be valid JSON: {exc}') from exc
    if not isinstance(overrides, dict):
        raise RealModeConfigurationError(f'{name} must be a JSON object of tag -> protocol address')
    unknown = sorted(set(overrides) - set(result))
    if unknown:
        raise RealModeConfigurationError(f'{name} contains unknown tags: {", ".join(unknown)}')
    for tag, address in overrides.items():
        if isinstance(address, bool) or not isinstance(address, int) or not 0 <= address <= 65535:
            raise RealModeConfigurationError(f'{name} address for {tag} must be an integer 0-65535')
        result[tag] = address
    return result


def load_real_config(env: Any = None) -> RealConfig:
    """Validate MODE=real settings. Never supplies simulation defaults for missing values."""
    env = os.environ if env is None else env
    mode = str(env.get('MODE', 'simulation')).strip().lower() or 'simulation'
    if mode not in ('simulation', 'real'):
        raise RealModeConfigurationError(f'MODE must be "simulation" or "real", got {mode!r}')

    strict = _env_bool(env, 'REAL_STRICT', True)
    allow_writes = _env_bool(env, 'ALLOW_WRITES', False)
    log_level = str(env.get('LOG_LEVEL', 'INFO')).strip().upper() or 'INFO'

    if mode == 'simulation':
        return RealConfig(
            mode, strict, allow_writes, log_level, '', 502, 1,
            dict(DEFAULT_REGISTER_MAP), dict(DEFAULT_COIL_MAP),
        )

    if not strict:
        raise RealModeConfigurationError(
            'REAL_STRICT=false is not allowed with MODE=real; silent fallback to simulation is forbidden'
        )
    missing = [name for name in ('MODBUS_HOST', 'MODBUS_PORT', 'MODBUS_UNIT_ID') if not _filled(env.get(name))]
    if missing:
        raise RealModeConfigurationError(
            'MODE=real requires explicit configuration; missing or placeholder values: ' + ', '.join(missing)
        )
    return RealConfig(
        mode=mode,
        strict=strict,
        allow_writes=allow_writes,
        log_level=log_level,
        host=str(env['MODBUS_HOST']).strip(),
        port=_env_int(env, 'MODBUS_PORT', 502, 1, 65535),
        unit_id=_env_int(env, 'MODBUS_UNIT_ID', 1, 1, 247),
        register_map=_load_address_map(env, 'MODBUS_REGISTER_MAP', DEFAULT_REGISTER_MAP),
        coil_map=_load_address_map(env, 'MODBUS_COIL_MAP', DEFAULT_COIL_MAP),
    )


class ModbusConveyorAdapter:
    """Read-only-by-default Modbus TCP source with the simulator's snapshot contract."""

    def __init__(self, env: Any = None):
        self.config = load_real_config(env)
        if self.config.mode != 'real':
            raise RealModeConfigurationError('ModbusConveyorAdapter requires MODE=real')
        self.register_map = self.config.register_map
        self.coil_map = self.config.coil_map
        self._client = None

    def connect(self) -> 'ModbusConveyorAdapter':
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as exc:
            raise RealModeDependencyError(
                'MODE=real requires pymodbus>=3.8; install requirements-real.txt on the target host. '
                'No simulation fallback is available.'
            ) from exc
        client = ModbusTcpClient(self.config.host, port=self.config.port, timeout=5)
        try:
            connected = client.connect()
        except Exception as exc:
            raise RealModeError(
                f'Cannot connect to Modbus TCP host {self.config.host}:{self.config.port}: {exc}'
            ) from exc
        if not connected:
            raise RealModeError(
                f'Cannot connect to Modbus TCP host {self.config.host}:{self.config.port} '
                f'(unit {self.config.unit_id})'
            )
        self._client = client
        return self

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def _unit_kwargs(self, method) -> dict[str, int]:
        code = getattr(method, '__code__', None)
        if code is None:
            return {}
        names = code.co_varnames
        for name in ('unit', 'slave'):
            if name in names:
                return {name: self.config.unit_id}
        if code.co_flags & 0x08:
            return {'unit': self.config.unit_id}
        return {}

    def _response(self, function: str, address: int, **kwargs: Any) -> Any:
        if self._client is None:
            raise RealModeError('Modbus client is not connected; call connect() first')
        method = getattr(self._client, function)
        try:
            response = method(address, **self._unit_kwargs(method), **kwargs)
        except Exception as exc:
            raise RealModeError(f'Modbus {function} failed at address {address}: {exc}') from exc
        if getattr(response, 'isError', lambda: False)():
            raise RealModeError(f'Modbus {function} returned an error at address {address}: {response}')
        return response

    def read_register(self, tag: str) -> int:
        if tag not in self.register_map:
            raise RealModeConfigurationError(f'No register address configured for tag {tag!r}')
        address = self.register_map[tag]
        response = self._response('read_holding_registers', address, count=1)
        return int(response.registers[0])

    def read_coil(self, tag: str) -> bool:
        if tag not in self.coil_map:
            raise RealModeConfigurationError(f'No coil address configured for tag {tag!r}')
        address = self.coil_map[tag]
        response = self._response('read_coils', address, count=1)
        return bool(response.bits[0])

    def snapshot(self) -> dict[str, Any]:
        from conveyor_simulator import STATE_NAMES

        values = {tag: self.read_register(tag) for tag in self.register_map}
        values['Conveyor_Run'] = int(self.read_coil('Conveyor_Run'))
        values['Auto_Mode'] = int(self.read_coil('Auto_Mode'))
        values['StateName'] = STATE_NAMES.get(values['State'], 'UNKNOWN')
        values['source'] = 'real-modbus'
        values['elapsed_s'] = 0.0
        return values

    def tick(self, dt: float = 0.2) -> dict[str, Any]:
        del dt
        return self.snapshot()

    def _require_writes(self) -> None:
        if not self.config.allow_writes:
            raise WriteNotAllowedError(
                'Writes are disabled; set ALLOW_WRITES=true explicitly to command the PLC. '
                'Physical E-stop and jam circuits cannot be bypassed in software.'
            )

    def write_coil(self, tag: str, value: bool) -> None:
        self._require_writes()
        if tag not in self.coil_map:
            raise RealModeConfigurationError(f'No coil address configured for tag {tag!r}')
        self._response('write_coil', self.coil_map[tag], value=bool(value))

    def write_register(self, tag: str, value: int) -> None:
        self._require_writes()
        if tag not in self.register_map:
            raise RealModeConfigurationError(f'No register address configured for tag {tag!r}')
        self._response('write_register', self.register_map[tag], value=int(value) & 0xFFFF)

    def start(self) -> None:
        self.write_coil('Conveyor_Run', True)

    def stop(self) -> None:
        self.write_coil('Conveyor_Run', False)

    def reset(self) -> None:
        self.write_coil('Reset_Alarms', True)

    def set_speed(self, percent: float) -> None:
        self.write_register('Belt_Speed_pct', min(100.0, max(0.0, float(percent))))


def create_conveyor_source(env: Any = None, source: str | None = None):
    """Factory: ConveyorSimulator by default, connected Modbus client for real mode."""
    env = os.environ if env is None else env
    mode_env = str(env.get('MODE', 'simulation')).strip().lower() or 'simulation'
    requested = source if source is not None else mode_env
    mode = str(requested).strip().lower()
    if mode not in ('simulation', 'real'):
        raise RealModeConfigurationError(f'source must be "simulation" or "real", got {requested!r}')
    if mode == 'simulation':
        from conveyor_simulator import ConveyorSimulator

        return ConveyorSimulator()
    if mode_env != 'real':
        raise RealModeConfigurationError(
            'MODE=real must be set in the environment before the real source can be selected'
        )
    return ModbusConveyorAdapter(env=env).connect()
