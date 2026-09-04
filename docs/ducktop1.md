# ducktop1

ducktop1 was my first version of this laptop idea. it used a Raspberry Pi
500+ and a 16-inch 2560x1600 portable monitor in a custom case. it worked,
including the display at up to 90 Hz, but the packaging was awkward.

the HDMI and USB-C cables had to loop around the outside of the case.
the keyboard, trackpad, display, and power system were still separate
things, and the monitor controller decided too much of the internal layout.

ducktop2 keeps the 16-inch format, mechanical keyboard, battery operation,
and exposed maker hardware. it moves to an x86 Mu module and custom boards,
with the display connected directly over eDP. the carrier was later split
into several boards to fit the build.

the original display was damaged while being opened, although its LCD
still worked. the teardown helped identify the panel and controller
connections. a replacement AUO B160QAN03.K was later tested successfully
at 2560x1600 and 120 Hz using the Intehill controller.

[ducktop2](../README.md) and [the current display work](display-direct-edp.md)
pick up from there.
