# Cyphercon9 Badge Firmware

MicroPython firmware for the Cyphercon9 conference badge, running on a Raspberry Pi Pico with an SX1262 LoRa radio, 132x32 LCD display, 6 red LEDs, buttons, and a vibration motor.

## Updating the Badge

Connect the badge to your computer via USB. The badge exposes a serial REPL (no mass storage).

**Install mpremote** (one time):

```bash
pip install mpremote
```

**Transfer firmware:**

```bash
mpremote connect /dev/cu.usbmodem101 cp blue-badge.py :main.py
```

**Monitor debug output:**

```bash
screen /dev/cu.usbmodem101
```

> Note: Only one program can use the serial port at a time. Quit `screen` (Ctrl-A, K) before using `mpremote`.

## Features

### Hardware

- **Display**: 132x32 pixel LCD (SPI) with character/glyph rendering
- **LEDs**: 7 total (1 Pico onboard LED + 6 external red LEDs) with rotation, pulse, and chase animations
- **Buttons**: Social button + two 3-way switch groups (up/down/push each)
- **Radio**: SX1262 LoRa for badge-to-badge communication
- **IR**: 38kHz IR transmitter via PIO state machine
- **Vibration motor**: For notifications

### Modes

| Mode | Description |
|------|-------------|
| **Idle** | Home screen with scrolling text, random animations, and LED light show. Shows mail indicator when unread messages exist. |
| **Alias** | Edit your 16-character display name. Cycle through glyphs with up/down, move cursor with left/right, shift to toggle character set. |
| **Inbox** | Browse up to 32 received messages. Navigate with up/down, mark as read with button press. |
| **Compose (Page 1)** | Select a recipient from known contacts. |
| **Compose (Page 2)** | Write a 16-character message using glyph selection. Send with the social button. |

### Radio / Networking

- **Direct messages** (pages) and **broadcasts** relayed by other badges
- Checksum and sync word validation on all packets
- Echo detection to ignore your own retransmitted packets
- Queue system for pending transmissions
- Badge hierarchy based on serial number ranges (founder, extreme, lifetime, speaker, general, vendor) with different relay permissions

### Persistent Storage

- **serial**: Unique 2-byte badge identifier
- **alias_memory**: Contact names (676 entries x 16 bytes)
- **social_memory**: Tracks which badges you've encountered
- **inbox_memory**: Received messages with unread tracking

## Changes in This Branch (`input_refactor`)

### Compose Cursor Remembers Previous Letter

When composing a message and moving to the next character position, the cursor now starts at the same letter you previously selected instead of resetting to the beginning of the character list. This makes typing words with repeated or nearby letters much faster.

### Idle LED Light Show

When the badge is idle with no unread messages, the LEDs perform a repeating light show:

1. **Clockwise chase** — a single LED chases around the ring (12 steps, ~1.8s)
2. **Counter-clockwise chase** — reverses direction (12 steps, ~1.8s)
3. **Off** — all LEDs turn off for 20 seconds
4. **Repeat**

The mail notification (LED rotate) still takes priority when unread messages exist. The light show is distinct from the mail indicator so you can tell them apart at a glance.
