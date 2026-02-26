import board
import busio
import displayio
import digitalio
import time
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_imageload

MIRROR = True

# Constants
IMAGE_FILE = "sprites/gps_load.bmp"
SPRITE_SIZE = (32, 32)
FRAMES = 28
DISPLAY_WIDTH = 133
DISPLAY_HEIGHT = 64

# Splash screen variables
SPLASH_DURATION = 1.0
splash_start_time = 0.0
show_splash = False
current_splash_mode = None

# Initialize display
displayio.release_displays()

sda, scl = board.GP0, board.GP1
i2c = busio.I2C(scl, sda)

display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64, rotation=0)

# Create a display group
display_group = displayio.Group()

# Load the sprite sheet
icon_bit, icon_pal = adafruit_imageload.load(IMAGE_FILE, bitmap=displayio.Bitmap, palette=displayio.Palette)

splash_screens = {
    'speed': adafruit_imageload.load("sprites/speed_.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette),
    'altitude': adafruit_imageload.load("sprites/altitude_.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette),
    'satellites': adafruit_imageload.load("sprites/satellites_.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
}

# Extend the display group to support multiple layers
# display_group.pop()  # Remove the existing text area
splash_group = displayio.Group()
display_group.append(splash_group)

# Create TileGrid for animation
sprite_grid = displayio.TileGrid(
    icon_bit,
    pixel_shader=icon_pal,
    width=1,
    height=1,
    tile_height=SPRITE_SIZE[1],
    tile_width=SPRITE_SIZE[0],
    default_tile=0,
    x=(DISPLAY_WIDTH - SPRITE_SIZE[0]) // 2,  # Center horizontally
    y=(DISPLAY_HEIGHT - SPRITE_SIZE[1]) // 2  # Center vertically
)

display_group.append(sprite_grid)
display.root_group = display_group

# Initialize GPS module
uart = busio.UART(board.GP4, board.GP5, baudrate=9600, timeout=10)

# Initialize LED
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False  # LED indicates GPS activity

# Initialize button
button = digitalio.DigitalInOut(board.GP15)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Font and text area setup
font_name = "fonts/terminal_reversed.bdf" if MIRROR else "fonts/terminal.bdf"
font = bitmap_font.load_font(font_name)
text_area = label.Label(
    font,
    color=0xFFFF00,
    x=0,
    y=DISPLAY_HEIGHT // 2,  # Center vertically
    scale=5,
    label_direction='RTL' if MIRROR else 'LTR',
)
display_group.append(text_area)

# Display modes
DISPLAY_MODES = ['speed', 'altitude', 'satellites', 'fix']
current_mode = 0  # Start with speed mode

# GPS data storage
gps_data = {
    'speed': None,
    'altitude': None,
    'satellites': None,
    'fix': False
}

# Animation variables
last_animation_update = 0.0
current_frame = 1

def parse_gprmc(sentence):
    """Parse GPRMC sentence and return speed in km/h."""
    try:
        parts = sentence.split(',')
        if len(parts) < 8 or parts[2] != 'A':
            return None
        speed_knots = float(parts[7])
        return speed_knots * 1.852  # Convert knots to km/h
    except (ValueError, IndexError, TypeError):
        return None


def parse_gpgga(sentence):
    """Parse GPGGA sentence and return tuple (quality, satellites, altitude)."""
    try:
        parts = sentence.split(',')
        if len(parts) < 10:
            return None
        quality = int(parts[6]) if parts[6] else 0
        satellites = int(parts[7]) if parts[7] else 0
        altitude = float(parts[9]) if parts[9] else 0
        return (quality, satellites, altitude)
    except (ValueError, IndexError, TypeError):
        return None


def display_number(area, number):
    center = int(DISPLAY_WIDTH / 2)
    number = str(number)
    
    try:
        if number == "N/A":
            area.x = center + 45 if MIRROR else center - 45
            return
        elif len(number) == 3:
            area.x = center + 45  if MIRROR else center - 45
        elif len(number) == 2:
            area.x = center + 30 if MIRROR else center - 30
        elif len(number) == 1:
            area.x = center + 15 if MIRROR else center - 15
    except:
        pass
    area.text = str(number)


def update_display():
    """Update display based on current mode and data."""
    mode = DISPLAY_MODES[current_mode]
    sprite_grid[0] = 0
    value = 0
    if mode == 'speed':
        value = gps_data['speed']
        if value is None:
            display_number(text_area, "N/A")
        else:
            display_number(text_area, str(int(value)))
    elif mode == 'altitude':
        value = gps_data['altitude']
        if value is None:
            display_number(text_area, "N/A")
        else:
            display_number(text_area, str(int(value)))
    elif mode == 'satellites':
        value = gps_data['satellites']
        if value is None:
            display_number(text_area, "N/A")
        else:
            display_number(text_area, str(int(value)))
    elif mode == 'fix':
        value = gps_data['fix']
        display_number(text_area, "")
    if value is not None:
        print(f'{mode}: {value}')
    
    # Center the text
    # text_area.x = (DISPLAY_WIDTH - text_area.width) // 2


def handle_button_press():
    splash_group = displayio.Group()  # Reset splash group to be completely new
    display_group.append(splash_group)  # Add to display group
    """Handle button press to switch display modes and show splash screen."""
    global current_mode, show_splash, splash_start_time, current_splash_mode, text_area

    current_mode = (current_mode + 1) % len(DISPLAY_MODES)
    mode = DISPLAY_MODES[current_mode]
    print(f"Switching to mode: {mode}")

    # Clear previous text to avoid overlapping
    text_area.text = ""

    # If not in "fix" mode, show splash screen
    if mode != "fix":
        splash_start_time = time.monotonic()
        show_splash = True
        current_splash_mode = mode

        # Remove existing splash screens
        while len(splash_group) > 0:
            splash_group.pop()

        # Load the correct splash image
        if mode in splash_screens:
            splash_bit, splash_pal = splash_screens[mode]
            splash_grid = displayio.TileGrid(
                splash_bit,
                pixel_shader=splash_pal,
                x=(DISPLAY_WIDTH - splash_bit.width) // 2,
                y=(DISPLAY_HEIGHT - splash_bit.height) // 2
            )
            splash_group.append(splash_grid)
            
            # Ensure splash group is displayed
            if splash_group not in display_group:
                display_group.append(splash_group)

            display.root_group = display_group
            display.refresh()

        # Wait for splash duration
        time.sleep(SPLASH_DURATION)

        # Remove splash screen safely
        while len(splash_group) > 0:
            splash_group.pop()

        show_splash = False

    # Ensure fix mode clears the screen completely
    if mode == "fix":
        text_area.text = ""  # Clear text
        while len(splash_group) > 0:
            splash_group.pop()  # Ensure no splash remains
        if splash_group in display_group:
            display_group.remove(splash_group)  # Remove group if it exists
        display.root_group = display_group
        display.refresh()


def animate_sprite(time_now):
    """Update animation frame."""
    global current_frame, last_animation_update
    text_area.text = ""
    if time_now - last_animation_update >= 0.02:
        sprite_grid[0] = current_frame
        current_frame = (current_frame % (FRAMES - 1)) + 1
        last_animation_update = time_now


try:
    while True:
        current_time = time.monotonic()
        
        # Check button state
        if not button.value:  # Button pressed
            handle_button_press()
            time.sleep(0.2)  # Debounce delay
            
        # Read GPS data
        raw_sentence = uart.readline()
        if raw_sentence:
            try:
                sentence = raw_sentence.decode("utf-8").strip()
            except UnicodeError:
                sentence = ''
            if sentence.startswith('$GPRMC'):
                speed = parse_gprmc(sentence)
                print(speed)
                if speed is not None:
                    gps_data['speed'] = speed
                    gps_data['fix'] = True
                    led.value = False
            elif sentence.startswith('$GPGGA'):
                gpgga_data = parse_gpgga(sentence)
                print(gpgga_data)
                if gpgga_data:
                    quality, satellites, altitude = gpgga_data
                    gps_data.update({
                        'altitude': altitude,
                        'satellites': satellites,
                        'fix': quality > 0
                    })
                    led.value = False
            else:
                # Unknown sentence type
                led.value = True
                pass
                
        # Update display
        if not gps_data['fix']:
            animate_sprite(current_time)
            # display_number(text_area, 823)
        else:
            update_display()
        
        display.refresh()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Program terminated by user")
finally:
    # Cleanup resources
    display_group.pop()
    display.root_group = None
    displayio.release_displays()