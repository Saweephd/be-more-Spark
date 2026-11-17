# BMO button board firmware

`bmo_controller/bmo_controller.ino` runs on the Adafruit Feather 32u4 Basic Proto
soldered to the BMO controller board. It makes the seven face buttons appear to the
Raspberry Pi as a USB keyboard.

| Button | Feather pin | Key |
|---|---|---|
| D-pad up | 5 | Up arrow |
| D-pad right | 6 | Right arrow |
| D-pad down | 9 | Down arrow |
| D-pad left | 10 | Left arrow |
| Triangle | 11 | Left Shift |
| Small circle | 12 | Enter |
| Big circle | 13 | Space |

The pin assignments come from the controller board designed by brenpoly
(https://www.printables.com/model/1582055). The board files are his and are not
copied here.

## Flashing

Board: "Adafruit Feather 32u4" from the Adafruit AVR Boards package. Needs the
Arduino `Keyboard` library. If the port does not appear, press the Feather's reset
button twice quickly to enter the bootloader, then upload within eight seconds.

From BMO itself: `ops/bmo-ctl.sh flash-buttons` builds this sketch and loads it onto the Feather, and `ops/bmo-ctl.sh buttons` shows each press as the Pi receives it. Both need the Feather's USB cable plugged into the Pi and `arduino-cli` in `~/.local/bin`.
