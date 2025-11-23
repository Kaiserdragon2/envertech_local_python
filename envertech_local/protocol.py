#protocol.py
import asyncio
import logging
from .utils import parse_module_data

_LOGGER = logging.getLogger(__name__)

class InverterClient:
    def __init__(self, ip: str, port: int, sn: str):
        self.ip = ip
        self.port = port
        self.sn = sn
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        _LOGGER.info(f"Connected to inverter at {self.ip}:{self.port}")

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            _LOGGER.info("Disconnected from inverter")

    async def send_command(self, data: bytes):
        if self.writer is None:
            await self.connect()
        if not data:
            _LOGGER.error("No data to send. Command aborted.")
            return
        self.writer.write(data)
        await self.writer.drain()

    async def receive_data(self, timeout=5):
        try:
            raw = await asyncio.wait_for(self.reader.read(1024), timeout=timeout)
            return list(raw)
        except asyncio.TimeoutError:
            return None

    def parse_data(self, raw: list[int]) -> tuple[dict, int | None]:
        if not raw or len(raw) < 22:
            return {}, None

        control_code = int.from_bytes(raw[4:6], "big")
        data = {}
        number_of_panels = None

        if control_code == 4177:
            number_of_panels = (len(raw) - 22) // 32
            for i in range(number_of_panels):
                base = 20 + i * 32
                offset = {
                    "mi_sn": base,
                    "input_voltage": base + 6,
                    "power": base + 8,
                    "energy": base + 10,
                    "temperature": base + 14,
                    "grid_voltage": base + 16,
                    "frequency": base + 18,
                }
                parsed = parse_module_data(raw, offset)
                if parsed:
                    for k, v in parsed.items():
                        key = f"{i}_{k}"
                        data[key] = round(v, 2) if isinstance(v, (int, float)) else v

            # Sum totals
            for key in ["power", "energy"]:
                total = sum(data.get(f"{i}_{key}", 0) for i in range(number_of_panels))
                data[f"total_{key}"] = round(total, 2)

            # Firmware version
            data["firmware_version"] = f"{raw[10]}/{raw[12]}"

        elif control_code == 4102:
            # Command recognized but no meaningful data to return
            data = {}
            number_of_panels = None

        else:
            # Unknown control code — could log or ignore
            data = {}
            number_of_panels = None

        return data, number_of_panels, control_code

