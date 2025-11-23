#utils.py
def check_cs(byte_array):
    return (sum(byte_array) + 85) & 0xFF

def to_int16(byte1, byte2):
    return byte1 * 256 + byte2

def to_int32(byte1, byte2, byte3, byte4):
    return (byte1 << 24) + (byte2 << 16) + (byte3 << 8) + byte4

def parse_module_data(data, offset):
    try:
        return {
            "mi_sn": "".join(f'{data[offset["mi_sn"]+i]:02x}' for i in range(4)),
            "input_voltage": to_int16(data[offset["input_voltage"]], data[offset["input_voltage"] + 1]) * 64 / 32768,
            "power": to_int16(data[offset["power"]], data[offset["power"] + 1]) * 512 / 32768,
            "energy": to_int32(
                data[offset["energy"]],
                data[offset["energy"] + 1],
                data[offset["energy"] + 2],
                data[offset["energy"] + 3],
            ) * 4 / 32768,
            "temperature": to_int16(data[offset["temperature"]], data[offset["temperature"] + 1]) * 256 / 32768 - 40,
            "grid_voltage": to_int16(data[offset["grid_voltage"]], data[offset["grid_voltage"] + 1]) * 512 / 32768,
            "frequency": to_int16(data[offset["frequency"]], data[offset["frequency"] + 1]) * 128 / 32768,
        }
    except IndexError:
        return None
