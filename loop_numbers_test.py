import board, busio, displayio, os, terminalio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
import time

displayio.release_displays()

board_type = os.uname().machine
print(f"Board: {board_type}")

sda, scl = board.GP0, board.GP1

i2c = busio.I2C(scl, sda)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

# Make the display context
splash = displayio.Group()

# Set the root group of the display to the splash group
display.root_group = splash

# Load a larger font
font = terminalio.FONT

# Initial number to display
number = 0

# Create a label for displaying the number
text_area = label.Label(font, text=str(number), color=0xFFFF00, x=1, y=35, scale=7)
splash.append(text_area)


def display_number(area, number):
    if number >= 100:
        area.x=1
    elif number >= 10:
        area.x=25
    else:
        area.x=50

    area.text = str(number)


while True:
    # Update the text with the current number
    display_number(text_area, number)
    
    # Increment the number
    number = (number + 1) % 121  # Loop back to 0 after 120
    
    # Wait for a short period before updating the display
    time.sleep(0.2)

