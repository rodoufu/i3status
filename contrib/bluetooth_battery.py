import argparse
import json
import subprocess
import sys
from enum import Enum
from typing import List


class bcolors(Enum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def colored(self, text: str) -> str:
        return f"{self.value}{text}{self.ENDC.value}"


def call_process_get_output(cli: List[str]) -> str:
    process = subprocess.Popen(cli, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.wait()
    output, _errors = process.communicate()
    return output.decode()


def get_bluetooth_battery(
    is_debug: bool,
    battery_red: int,
    battery_yellow: int,
    ignore_colors: bool,
) -> List[str]:
    devices_output = call_process_get_output(["bluetoothctl", "devices"]).splitlines()
    device_name_id_map = {
        x[1].strip(): x[0].strip()
        for x in map(
            lambda x: [x[: x.find(" ")], x[x.find(" ") + 1 :]],
            map(lambda x: x.lstrip("Device").strip(), devices_output),
        )
    }

    line = []
    for device_name, device_id in device_name_id_map.items():
        device_info = call_process_get_output(
            ["bluetoothctl", "info", device_id]
        ).splitlines()

        def find_and_clean_up(info, to_find):
            return map(
                lambda x: x[x.find(": ") + 1 :].strip(),
                filter(lambda x: x.find(to_find) != -1, info),
            )

        icon = next(find_and_clean_up(device_info, "Icon"), None)
        is_connected = next(find_and_clean_up(device_info, "Connected"), "no")
        is_connected = is_connected == "yes"
        battery = next(
            map(
                lambda x: float(x[x.find("(") + 1 : x.find(")")]),
                find_and_clean_up(device_info, "Battery Percentage"),
            ),
            None,
        )

        if is_debug:
            print(
                f"name: {device_name}, icon: {icon}, connected: {is_connected}, battery: {battery}"
            )

        icon_name_symbol = {
            "input-mouse": "󰍽",
            "input-keyboard": "",
            "audio-headset": "",
            "audio-headphones": "",
        }

        if icon:
            icon = icon_name_symbol.get(icon)

        if is_connected and battery is not None:
            batery_text = f"{battery:.0f}%"
            if icon:
                batery_text = f"{icon} {batery_text}"
            else:
                batery_text = f"{device_name} {batery_text}"

            if not ignore_colors:
                if battery_red <= battery <= battery_yellow:
                    batery_text = bcolors.WARNING.colored(batery_text)
                elif battery < battery_red:
                    batery_text = bcolors.FAIL.colored(batery_text)

            line.append(batery_text)

    return line


def print_line(message):
    """Non-buffered printing to stdout."""
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def read_line():
    """Interrupted respecting reader for stdin."""
    # try reading a line, removing any extra whitespace
    try:
        line = sys.stdin.readline().strip()
        # i3status sends EOF, or an empty line
        if not line:
            sys.exit(3)
        return line
    # exit on ctrl-c
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", help="Run in debug mode", action="store_true")
    parser.add_argument(
        "--ignore-colors", help="Ignore printing using colors", action="store_true"
    )
    parser.add_argument(
        "--battery_red", help="Battery level to print red", type=int, default=20
    )
    parser.add_argument(
        "--battery_yellow", help="Battery level to print red", type=int, default=50
    )
    args = parser.parse_args()

    # FIXME: the colors are not working anymore in the status bar

    if args.debug:
        content = " ".join(
            get_bluetooth_battery(
                is_debug=args.debug,
                battery_yellow=args.battery_yellow,
                battery_red=args.battery_red,
                ignore_colors=args.ignore_colors,
            )
        )
        print(f"args: {args}")
        print(content)
    else:
        # Skip the first line which contains the version header.
        print_line(read_line())

        # The second line contains the start of the infinite array.
        print_line(read_line())

        while True:
            line, prefix = read_line(), ""
            # ignore comma at start of lines
            if line.startswith(","):
                line, prefix = line[1:], ","

            content = " ".join(
                get_bluetooth_battery(
                    is_debug=args.debug,
                    battery_yellow=args.battery_yellow,
                    battery_red=args.battery_red,
                    ignore_colors=args.ignore_colors,
                )
            )

            j = json.loads(line)
            # insert information into the start of the json, but could be anywhere
            # CHANGE THIS LINE TO INSERT SOMETHING ELSE
            j.insert(
                0,
                {
                    "full_text": "%s" % content,
                    "name": "bluetooth_battery",
                },
            )
            # and echo back new encoded json
            print(prefix + json.dumps(j))
            # print_line(prefix + json.dumps(j))
            sys.stdout.flush()
