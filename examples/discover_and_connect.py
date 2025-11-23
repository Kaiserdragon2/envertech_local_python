import asyncio
from tabulate import tabulate
from envertech_local import discover_devices_async, get_inverter_data


def print_parsed_data_table(parsed_data, device_label=None):
    # Step 1: Group keys per panel
    panel_data = {}
    global_data = {}

    for key, value in parsed_data.items():
        if "_" in key and key[0].isdigit():
            panel_index, metric = key.split("_", 1)
            panel_data.setdefault(panel_index, {})[metric] = value
        else:
            global_data[key] = value

    # Optional: Label per device
    if device_label:
        print(f"\n🔎 Device: {device_label}")

    # Step 2: Sort panels and prepare table rows
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

    # Step 3: Print table
    print(f"\n✅ Found {len(panel_data)} panels\n")
    print(tabulate(table, headers=headers, tablefmt="pretty"))

    # Step 4: Show global summary
    print("\n📊 Summary:")
    if "total_power" in global_data:
        print(f"  🔋 Total Power:   {global_data['total_power']} W")
    if "total_energy" in global_data:
        print(f"  ⚡ Total Energy:  {global_data['total_energy']} kWh")
    if "firmware_version" in global_data:
        print(f"  🧠 Firmware:      {global_data['firmware_version']}")


async def main():
    devices = await discover_devices_async(timeout=5)
    if not devices:
        print("No devices found.")
        return

    print(f"\n🔍 {len(devices)} device(s) found.")

    for i, device in enumerate(devices, 1):
        label = f"{device.get('ip')} (SN: {device.get('serial_number')})"
        try:
            parsed_data, panelcount, control_code = await get_inverter_data(device)
            if parsed_data and panelcount:
                print_parsed_data_table(parsed_data, device_label=label)
            else:
                print(f"⚠️  No data received from device {label}")
        except Exception as e:
            print(f"❌ Error retrieving data from device {label}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
