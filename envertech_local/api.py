# api.py
import asyncio
from typing import AsyncGenerator
from .protocol import InverterClient 
from .commands import build_inverter_break_command, build_inverter_request

async def get_inverter_data(device: dict, port: int = 14889, timeout: int = 20) -> dict:
    """
    Given a device dictionary with 'ip' and 'serial_number',
    connects to the inverter and returns parsed data.
    """
    ip = device.get("ip")
    sn = device.get("serial_number")

    if not ip or not sn:
        raise ValueError("Device must have 'ip' and 'serial_number' keys")

    client = InverterClient(ip, port, sn)

    try:
        await client.connect()
        await client.send_command(build_inverter_request(sn))  # Send start command

        for _ in range(5):  # Max 5 retries (adjust if needed)
            raw_data = await client.receive_data(timeout=timeout)
            if raw_data:
                data, panel_count, control_code = client.parse_data(raw_data)
                if data or panel_count is not None:
                    return data, panel_count, control_code
                else:
                    continue  # Retry if 4102 or unrecognized
            await asyncio.sleep(0.5)  # Wait before retrying
            await client.send_command(build_inverter_request(sn))  # Send start command
        return {}  # Give up after retries

    finally:
        await client.send_command(build_inverter_break_command(sn))  # Send stop command
        await client.disconnect()

async def stream_inverter_data(
    device: dict,
    port: int = 14889,
    interval: float = 5,
    timeout: int = 10
) -> AsyncGenerator[dict, None]:
    ip = device.get("ip")
    sn = device.get("serial_number")

    if not ip or not sn:
        raise ValueError("Device must have 'ip' and 'serial_number' keys")

    client = InverterClient(ip, port, sn)
    response_queue = asyncio.Queue()

    async def sender():
        """Send requests periodically."""
        try:
            while True:
                await client.send_command(build_inverter_request(sn))
                await asyncio.sleep(interval)
        except Exception as e:
            await response_queue.put({"error": f"Sender failed: {e}"})

    async def receiver():
        """Continuously receive data and push it into the queue."""
        try:
            while True:
                raw_data = await client.receive_data(timeout=1)
                if raw_data:
                    await response_queue.put(raw_data)
        except asyncio.TimeoutError:
            pass  # ignore timeouts
        except Exception as e:
            await response_queue.put({"error": f"Receiver failed: {e}"})

    await client.connect()
    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        while True:
            try:
                result = await asyncio.wait_for(response_queue.get(), timeout=timeout)
                if isinstance(result, dict) and "error" in result:
                    yield result
                    break

                # Parse inverter response
                data, panel_count, control_code = client.parse_data(result)

                if data or panel_count is not None:
                    yield data

            except asyncio.TimeoutError:
                # No response received in timeout window
                yield {}

    except Exception as e:
        yield {"error": str(e)}

    finally:
        sender_task.cancel()
        receiver_task.cancel()
        await client.send_command(build_inverter_break_command(sn))
        await client.disconnect()

