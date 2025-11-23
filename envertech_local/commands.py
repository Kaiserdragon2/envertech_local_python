#commands.py
import logging
from .utils import check_cs

_LOGGER = logging.getLogger(__name__)

def build_inverter_command(
    current_id_hex: str,
    control_code_int: int,
    payload: bytes = b"",
    payload_padding: int = 0
) -> bytes:
    """
    Build a protocol-compliant inverter command.

    Args:
        current_id_hex (str): Inverter ID as 8/12-digit hex string.
        control_code_int (int): Integer control code (e.g. 4177 for 0x1051).
        payload (bytes): Optional payload bytes to include after ID.
        payload_padding (int): Number of 0x00 bytes to pad after payload.

    Returns:
        bytes: Final command frame, or b"" on error.
    """
    if len(current_id_hex) != 8:
        _LOGGER.error(f"Inverter ID hex string must be exactly 8 characters long, got {len(current_id_hex)}")
        return b""
    try:
        control_code_bytes = control_code_int.to_bytes(2, "big")
    except OverflowError as e:
        _LOGGER.error(f"Control code {control_code_int} is out of range: {e}")
        return b""

    # Build the base packet before length
    data = bytearray()
    data.append(0x68)
    data.append(0x00)  # Placeholder for length
    data.append(0x00)  # Placeholder for length
    data.append(0x68)
    data += control_code_bytes
    data += bytes.fromhex(current_id_hex)
    data += payload
    data += bytes([0x00] * payload_padding)

    # Total length includes everything after byte 3 + checksum + end
    total_length = len(data) + 2  # +1 checksum, +1 end byte
    data[1] = (total_length >> 8) & 0xFF  # high byte
    data[2] = total_length & 0xFF          # low byte

    checksum = check_cs(data)
    data.append(checksum)
    data.append(0x16)
    return bytes(data)

def build_inverter_request(current_id_hex: str) -> bytes:
    # 4215 = 0x1077 = data request
    return build_inverter_command(
        current_id_hex=current_id_hex,
        control_code_int=4215,
        payload_padding=20
    )

def build_inverter_break_command(current_id_hex: str) -> bytes:
    # 4161 = 0x1041 = break/disconnect
    return build_inverter_command(
        current_id_hex=current_id_hex,
        control_code_int=4161,
        payload_padding=10
    )

def build_inverter_powercontrol_command(current_id_hex: str, level: int) -> bytes:
    if not (0 <= level <= 255):
        _LOGGER.error(f"Level {level} out of valid byte range (0-255).")
        return b""
    payload = bytes([level])
    return build_inverter_command(
        current_id_hex=current_id_hex,
        control_code_int=4407,
        payload=payload,
        payload_padding=0
    )
