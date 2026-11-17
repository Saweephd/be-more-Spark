// BMO button board firmware for the Adafruit Feather 32u4 Basic Proto.
//
// Turns BMO's seven face buttons into ordinary USB keyboard keys, so the Pi
// (or any computer) sees a keyboard and every program can use the buttons.
//
// Wiring, taken from the net names in brenpoly's BMO_Controller_PCB board files
// (https://www.printables.com/model/1582055): each switch connects its pin to
// ground when pressed, so the pins use the internal pull-up and read LOW when
// pressed.
//
//   Feather pin   Button on the face   Key sent
//   -----------   ------------------   ----------------
//        5        D-pad up             Up arrow
//        6        D-pad right          Right arrow
//        9        D-pad down           Down arrow
//       10        D-pad left           Left arrow
//       11        Triangle             Left Shift  (button B / cancel)
//       12        Big circle           Space       (button A / talk)
//       13        Small circle         Enter       (start / menu)
//
// Keys are held for as long as the button is held, so games get real
// press-and-hold behaviour. Each button is debounced separately.

#include <Keyboard.h>

const uint8_t BUTTON_COUNT = 7;
const uint8_t PINS[BUTTON_COUNT] = {5, 6, 9, 10, 11, 12, 13};
const uint8_t KEYS[BUTTON_COUNT] = {
  KEY_UP_ARROW, KEY_RIGHT_ARROW, KEY_DOWN_ARROW, KEY_LEFT_ARROW,
  KEY_LEFT_SHIFT, ' ', KEY_RETURN
};

const unsigned long DEBOUNCE_MS = 12;      // ignore contact bounce shorter than this
const unsigned long STARTUP_DELAY_MS = 3000;  // let the host finish setting up USB

bool stableState[BUTTON_COUNT];            // true = pressed
bool lastReading[BUTTON_COUNT];
unsigned long lastChange[BUTTON_COUNT];

void setup() {
  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    pinMode(PINS[i], INPUT_PULLUP);
    stableState[i] = false;
    lastReading[i] = false;
    lastChange[i] = 0;
  }
  delay(STARTUP_DELAY_MS);
  Keyboard.begin();
}

void loop() {
  unsigned long now = millis();
  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    bool pressed = (digitalRead(PINS[i]) == LOW);
    if (pressed != lastReading[i]) {
      lastReading[i] = pressed;
      lastChange[i] = now;
    }
    if (pressed != stableState[i] && (now - lastChange[i]) >= DEBOUNCE_MS) {
      stableState[i] = pressed;
      if (pressed) {
        Keyboard.press(KEYS[i]);
      } else {
        Keyboard.release(KEYS[i]);
      }
    }
  }
  delay(1);
}
