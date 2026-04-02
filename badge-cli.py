#!/usr/bin/env python3
"""Interactive CLI for Cyphercon 9 badge control over USB serial."""

import sys
import argparse
import threading
import time

import serial
import serial.tools.list_ports


def find_badge_port():
    """Auto-detect the badge's USB serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "usbmodem" in p.device.lower() or "acm" in p.device.lower():
            return p.device
    return None


def reader_thread(ser, stop_event):
    """Background thread that reads and prints badge responses."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line.startswith("RSP:"):
                    handle_response(line)
                elif line:
                    # Debug output from badge
                    print(f"  [debug] {line}")
            else:
                time.sleep(0.05)
        except (serial.SerialException, OSError):
            if not stop_event.is_set():
                print("\n[!] Serial connection lost.")
                stop_event.set()
            break


def handle_response(line):
    """Parse and pretty-print RSP: lines from the badge."""
    parts = line.split(":", 3)
    if len(parts) < 2:
        print(f"  {line}")
        return

    rtype = parts[1]

    if rtype == "OK" and len(parts) >= 3:
        subcmd = parts[2]
        if subcmd == "BC":
            msg = parts[3] if len(parts) > 3 else ""
            print(f"  Broadcast sent: {msg}")
        elif subcmd == "PG":
            detail = parts[3] if len(parts) > 3 else ""
            print(f"  Page sent: {detail}")
        elif subcmd == "INBOX":
            count = parts[3] if len(parts) > 3 else "0"
            print(f"  --- {count} message(s) total ---")
        elif subcmd == "STATUS":
            detail = parts[3] if len(parts) > 3 else ""
            fields = detail.split(":")
            if len(fields) >= 4:
                print(f"  Serial:  {fields[0]}")
                type_names = {
                    "0": "ghost", "1": "founder", "2": "extreme",
                    "3": "lifetime", "4": "speaker", "5": "general", "6": "vendor"
                }
                print(f"  Type:    {type_names.get(fields[1], fields[1])}")
                print(f"  Alias:   {fields[2]}")
                print(f"  Unread:  {fields[3]}")
            else:
                print(f"  Status: {detail}")
        elif subcmd == "IDLE":
            print("  Idle display updated.")
        elif subcmd == "RESETIDLE":
            print("  Idle display reset to default.")
        elif subcmd == "MARKREAD":
            count = parts[3] if len(parts) > 3 else "0"
            print(f"  Marked {count} message(s) as read.")
        elif subcmd == "GETALIAS":
            name = parts[3] if len(parts) > 3 else ""
            print(f"  Alias: {name}")
        elif subcmd == "ALIAS":
            name = parts[3] if len(parts) > 3 else ""
            print(f"  Alias set to: {name}")
        elif subcmd == "DEL":
            idx = parts[3] if len(parts) > 3 else ""
            print(f"  Deleted message [{idx}].")
        else:
            print(f"  OK: {line}")

    elif rtype == "MSG":
        # RSP:MSG:index:status:type:from_id:alias:text
        detail = parts[2] if len(parts) > 2 else ""
        remaining = parts[3] if len(parts) > 3 else ""
        fields = (detail + ":" + remaining).split(":")
        if len(fields) >= 6:
            idx = fields[0]
            status = fields[1]
            etype = fields[2]
            from_id = fields[3]
            from_alias = fields[4]
            text = fields[5] if len(fields) > 5 else ""
            marker = "*" if status == "unread" else " "
            print(f"  {marker} [{idx:>2}] ({etype:>9}) from {from_alias} (#{from_id}): {text}")
        else:
            print(f"  MSG: {line}")

    elif rtype == "HELP":
        detail = ":".join(parts[2:]) if len(parts) > 2 else ""
        print(f"  {detail}")

    elif rtype == "ERR":
        detail = ":".join(parts[2:]) if len(parts) > 2 else ""
        print(f"  [error] {detail}")

    else:
        print(f"  {line}")


def send_command(ser, cmd):
    """Send a command string to the badge."""
    ser.write((cmd + "\n").encode("utf-8"))
    ser.flush()


def print_help():
    print("""
Badge CLI Commands:
  broadcast <message>          Send a broadcast message (16 chars max)
  page <badge_id> <message>    Send a direct message to a badge
  inbox                        List inbox messages
  delete <number>              Delete a message by its index number
  mark-read                    Mark all inbox messages as read
  status                       Show badge info
  idle <top> | <bottom>        Set custom idle display (use | to separate lines)
  reset-idle                   Reset idle display to default
  alias                        Show current alias
  alias <name>                 Set your badge alias
  help                         Show this help
  quit                         Exit CLI
""")


def interactive(ser):
    """Run the interactive command loop."""
    stop = threading.Event()
    reader = threading.Thread(target=reader_thread, args=(ser, stop), daemon=True)
    reader.start()

    # Give the reader a moment to start and flush any boot output
    time.sleep(0.5)

    print("Connected to badge. Type 'help' for commands.\n")

    try:
        while not stop.is_set():
            try:
                line = input("badge> ").strip()
            except EOFError:
                break

            if not line:
                continue

            parts = line.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "help":
                print_help()
            elif cmd == "broadcast" or cmd == "bc":
                if not arg:
                    print("  Usage: broadcast <message>")
                    continue
                send_command(ser, "BC:" + arg[:16])
            elif cmd == "page" or cmd == "pg":
                pg_parts = arg.split(None, 1)
                if len(pg_parts) < 2:
                    print("  Usage: page <badge_id> <message>")
                    continue
                send_command(ser, "PG:" + pg_parts[0] + ":" + pg_parts[1][:16])
            elif cmd == "inbox":
                send_command(ser, "INBOX")
            elif cmd == "mark-read" or cmd == "markread":
                send_command(ser, "MARKREAD")
            elif cmd == "delete" or cmd == "del":
                if not arg:
                    print("  Usage: delete <message_number>")
                    continue
                send_command(ser, "DEL:" + arg.strip())
            elif cmd == "status":
                send_command(ser, "STATUS")
            elif cmd == "idle":
                if not arg:
                    print("  Usage: idle <top_text> | <bottom_text>")
                    continue
                if "|" in arg:
                    top, bottom = arg.split("|", 1)
                    send_command(ser, "IDLE:" + top.strip()[:16] + ":" + bottom.strip()[:16])
                else:
                    send_command(ser, "IDLE:" + arg[:16] + ":")
            elif cmd == "reset-idle" or cmd == "resetidle":
                send_command(ser, "RESETIDLE")
            elif cmd == "alias":
                if not arg:
                    send_command(ser, "ALIAS")
                else:
                    send_command(ser, "ALIAS:" + arg[:16])
            else:
                # Send raw command for advanced use
                send_command(ser, line)

            # Brief pause to let response arrive
            time.sleep(0.2)

    except KeyboardInterrupt:
        print()

    stop.set()
    reader.join(timeout=1)


def main():
    parser = argparse.ArgumentParser(description="Cyphercon 9 Badge CLI")
    parser.add_argument("-p", "--port", help="Serial port (auto-detected if omitted)")
    parser.add_argument("-b", "--baud", type=int, default=115200,
                        help="Baud rate (default: 115200)")
    parser.add_argument("-c", "--command",
                        help="Send a single command and exit (e.g. 'BC:hello')")
    args = parser.parse_args()

    port = args.port or find_badge_port()
    if not port:
        print("No badge found. Use -p to specify the serial port.")
        print("Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device} - {p.description}")
        sys.exit(1)

    print(f"Opening {port} at {args.baud} baud...")
    try:
        ser = serial.Serial(port, args.baud, timeout=0.1)
    except serial.SerialException as e:
        print(f"Failed to open {port}: {e}")
        sys.exit(1)

    if args.command:
        send_command(ser, args.command)
        time.sleep(1)
        while ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("RSP:"):
                handle_response(line)
            elif line:
                print(f"  {line}")
        ser.close()
    else:
        try:
            interactive(ser)
        finally:
            ser.close()
            print("Disconnected.")


if __name__ == "__main__":
    main()
