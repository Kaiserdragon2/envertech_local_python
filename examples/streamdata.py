import envertech_local
from envertech_local import stream_inverter_data
import asyncio
from tabulate import tabulate


def print_parsed_data_table(parsed_data, device_label=None):
    # Step 1: Group panel data
    panel_data = {}
    global_data = {}

    for key, value in parsed_data.items():
        if "_" in key and key[0].isdigit():
            panel_index, metric = key.split("_", 1)
            panel_data.setdefault(panel_index, {})[metric] = value
        else:
            global_data[key] = value

    # Optional: Label for device
    if device_label:
        print(f"\n🔄 Update from {device_label}")

    # Step 2: Panel table
    headers = [
        "Panel",
        "MI SN",
        "Voltage (V)",
        "Power (W)",
        "Energy (kWh)",
        "Temp (°C)",
        "Grid (V)",
        "Freq (Hz)"
    ]

    table = []
    for panel_index in sorted(panel_data.keys(), key=int):
        pdata = panel_data[panel_index]
        row = [
            f"Panel {panel_index}",
            pdata.get("mi_sn", "-"),
            pdata.get("input_voltage", "-"),
            pdata.get("power", "-"),
            pdata.get("energy", "-"),
            pdata.get("temperature", "-"),
            pdata.get("grid_voltage", "-"),
            pdata.get("frequency", "-"),
        ]
        table.append(row)

    if table:
        print(tabulate(table, headers=headers, tablefmt="fancy_grid"))
    else:
        print("No panel data available.")

    # Step 3: Global data
    print("\n📊 Summary:")
    if "total_power" in global_data:
        print(f"  🔋 Total Power:   {global_data['total_power']} W")
    if "total_energy" in global_data:
        print(f"  ⚡ Total Energy:  {global_data['total_energy']} kWh")
    if "firmware_version" in global_data:
        print(f"  🧠 Firmware:      {global_data['firmware_version']}")
    print("-" * 60)


async def main():
    device = {"ip": "127.0.0.1", "serial_number": "30800000"}
    device_label = f"{device['ip']} (SN: {device['serial_number']})"

    async for data in stream_inverter_data(device, interval=5):
        if isinstance(data, dict) and "error" in data:
            print(f"❌ Error: {data['error']}")
        else:
            print_parsed_data_table(data, device_label=device_label)


# Run it
if __name__ == "__main__":
    asyncio.run(main())
