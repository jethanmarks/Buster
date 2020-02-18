# pylint: disable=bare-except

import time
import math
from digitalio import DigitalInOut, Direction, Pull
import audioio
import busio
import board
import neopixel
import adafruit_lis3dh
import gc

# CUSTOMIZE YOUR WEAPONS HERE:
BUSTER = (255, 200, 0)              # Standard Yellow Gauge Color
CHARGE_BUSTER = (0,100,255)         # Cyan color for charge buster
IDLE = (255,0,0)                    # Red color for emitter
AIR = (0,0,255)                     # Blue for Air Man
WOOD = (0,255,0)                    # Green for Wood Man
QUICK = (0,0,0)                     # Pink for Quick Man
FLASH = (255,0,150)                 # Purple for Flash Man
HEAT = (255,50,0)                   # Red Orange for Heat Man
BUBBLE = (196,202,206)              # Silver/ Gray for Bubble Man
METAL = (133,87,35)                 # Brown for Metal Man
CRASH = (255, 100, 0)               # Orange for Crash Man
GAUGE_COLOR = BUSTER                # Default Gauge color to yellow
EMMITER_COLOR = IDLE                # Default Emitter color to red
WEAPON_LIST = [BUSTER, AIR, WOOD, QUICK, FLASH, HEAT, BUBBLE, METAL, CRASH]
WEAPON_NAMES = ["Buster", "Air", "Wood", "Quick", "Flash", "Heat", "Bubble", "Metal", "Crash"]
ACTIVE_WEAPON = WEAPON_NAMES[0]
CHARGE_COUNTER = 0 
CHARGED = False
WEAPON_TRACKER = 0
AMMO = 15
AMMO2 = 16
AMMO_COUNTER = 0

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
SWAP_THRESHOLD = 350

NUM_PIXELS = 51
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9

enable = DigitalInOut(POWER_PIN)  
enable.direction = Direction.OUTPUT
enable.value =False

audio = audioio.AudioOut(board.A0)     # Speaker
mode = 0                               # Initial mode = OFF

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)                          # NeoPixels off ASAP on startup
strip.show()

switch = DigitalInOut(SWITCH_PIN)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

time.sleep(0.1)

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    print("playing", name)
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except:
        return

def power(sound, duration):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """
    prev = 0
    gc.collect()                   # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        fraction = elapsed / duration            # Animation time, 0.0 to 1.0
        fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
        threshold = int(NUM_PIXELS * fraction + 0.5)
        num = threshold - prev # Number of pixels to light on this pass
        if num != 0:
            strip[prev:threshold] = [COLOR_IDLE] * num
            strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= NUM_PIXELS * 0.00003
            prev = threshold

    strip.fill(COLOR_IDLE)                   # or all pixels set on
    strip.show()
    while audio.playing:                         # Wait until audio done
        pass

def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    @param color_1:  first color, as an (r,g,b) tuple
    @param color_2:  second color, as an (r,g,b) tuple
    @param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    @return: (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
            int(color_1[1] * weight_1 + color_2[1] * weight_2),
            int(color_1[2] * weight_1 + color_2[2] * weight_2))

def chargeShot():
    play_wav("chargeBlast.wav")
    strip[44:50] = CHARGE_BUSTER
    strip.show()
    time.sleep(1)
    strip[44:50] = IDLE
    strip.show()

def weaponFire(weaponName, weaponColor):
    play_wav(weaponName, loop=False)
    strip[44:50] = weaponColor
    strip.show()
    time.sleep(1)
    strip[44:50] = IDLE
    strip.show()
    if not weaponName == "Buster":
        if AMMO == 0:
            play_wav('empty')
        strip[AMMO] = (0,0,0)
        strip[AMMO2] = (0,0,0)
        AMMO -= 1
        AMMO2 += 1

def weaponSwap(weapon):
    AMMO = 15
    AMMO2 = 16
    strip.fill(0)                          # NeoPixels off ASAP on startup
    strip.show()
    for i in range(16):
        x = 31 - i
        strip[i] = weapon
        strip[x] = weapon
        strip.show()
        play_wav('fill')                   # Start playing 'fill' sound
        time.sleep(.1)                     # Sleep for .1 second

# Main program loop, repeats indefinitely
power('on', 1.7, False)         # Power up!

while True:
    if not switch.value:                    # button pressed?
        weaponFire(WEAPON_LIST[WEAPON_NAMES],WEAPON_LIST[WEAPON_TRACKER])
        while not switch.value:             # Wait for button release
            time.sleep(1)                 # to avoid repeated triggering
            CHARGE_COUNTER += 1
            if CHARGE_COUNTER == 2: #ADD AND CONDITION FOR BUTTON RELEASE
                CHARGED = True
                CHARGE_COUNTER = 0
    if CHARGED:
        chargeShot()
        
    x, y, z = accel.acceleration # Read accelerometer
    accel_total = x * x + z * z
    # (Y axis isn't needed for this, assuming Hallowing is mounted
    # sideways to stick.  Also, square root isn't needed, since we're
    # just comparing thresholds...use squared values instead, save math.)
    if accel_total > SWAP_THRESHOLD:   # Large acceleration = SWAP
        weaponSwap(WEAPON_LIST[WEAPON_TRACKER])
        WEAPON_TRACKER += 1

