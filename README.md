# e-Paper information display

Information display using a 4.3inch e-Paper UART module from Waveshare and a RasPi 4B

## Requirements

Dependencies from the requirements.txt file, plus [raspi-uart-waveshare](https://github.com/jarret/raspi-uart-waveshare) and ``fortune``.

Note for Raspberry Pi 4 users: the raspi-uart-waveshare library hardcodes the serial path to the one used on the Pi 3 and 2, you'll need to open the epaper.py file and replace it with ``/dev/ttyS0``.

You might need to change the keyboard input path, by default it's hardcoded to ``/dev/input/event0``.

Display 2 has a hardcoded segment that checks my homeserver, you might want to get rid of it.

## Usage

Run ``./info.py``.

Press the left and right arrow keys to change between displays ("slides"). Press Enter to reload the current display.

Press up to toggle pausing the autoadvance (normally the display switches to the next one every 20 seconds). A small pause icon will show up in the bottom right corner. **Note that pausing will reload the current display** due to the way the pause function works, so if you want to pause to save some information on screen, you're out of luck. (I might rewrite it to save the existing information when toggling at some point, though.)

## Adding a new display

(Note: a "display", in this context, is a "slide"; the clock, Message Of The Now, and system information are all separate displays.)

1. Make a new function that takes one argument: ``paper``.
2. Add whatever commands you want. See other displays for reference.
3. Add the display function to the ``displays`` list.

## Adding a new display, as in "epaper display" or whatever

I dunno, but it would probably require a ground-up rewrite of all the "displays" and the main function... the pause function may still be of use, though.

This is meant to work with ONE SPECIFIC DISPLAY, and support for other modules is not planned, unless I get another module myself.
