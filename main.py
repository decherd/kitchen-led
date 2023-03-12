import time
import ntptime
from machine import Pin, PWM
import network
from os.path import exists


UTC_TIMEZONE = 5
LEDS_PIN = 32
PIR_PIN = 33

ntptime.settime()
utc_offset = UTC_TIMEZONE * 60 * 60
actual_time = time.localtime(time.time() + utc_offset)

with open('log.txt', mode='a+') as f:
                f.write(f"Booted up at: {actual_time}")

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip

def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection


frequency = 5000
led = PWM(Pin(LEDS_PIN), frequency)
led.duty(0)

def led_ramp_to(led_pct):
    #Ramp up if led_pct is higher
    if led_pct * 1023 > led.duty():
        for duty_cycle in range(led.duty(), led_pct * 1024):
            led.duty(duty_cycle)
            time.sleep(0.005)
    else:
        for duty_cycle in range(led.duty(), led_pct * 1024, -1):
            led.duty(duty_cycle)
            time.sleep(0.005)


motion = False
def handle_interrupt(pin):
  global motion
  motion = True
  global interrupt_pin
  interrupt_pin = pin

# Modes
# - Sleep
#   - turns on for 5 minutes
# - 4:45am to 7am and 8pm - 9:30pm
#   - Runs at some percentage 70%?
# - Day
#   - Runs at 100%

SLEEP_MODE_PCT = .6
DAWN_DUSK_PCT = .6
DAY_PCT = 1
SLEEP_MODE_START = (21, 30)
DAWN_START = (5, 0)
DAY_START = (7, 0)
DUSK_START = (20,0)
SLEEP_MODE_ALARM_MINUTES = 5

pir = Pin(PIR_PIN, Pin.IN)
pir.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)
sleep_start = 0
connection = open_socket(ip)

while True:
    client = connection.accept()[0]
    request = client.recv(1024)
    request = str(request)
    with open('log.txt', mode='r') as f:
        client.send(f)
    client.close()
    actual_time = time.localtime(time.time() + utc_offset)
    # If it is Sleep Mode
    if (actual_time[3], actual_time[4]) >= SLEEP_MODE_START or (actual_time[3], actual_time[4]) < DAWN_START:
        if motion:
            led_ramp_to(SLEEP_MODE_PCT)
            sleep_start = time.time()
            motion = False
            with open('log.txt', mode='a+') as f:
                f.write(f"Detecting motion at: {actual_time}")
        if sleep_start and (time.time() - sleep_start >= (SLEEP_MODE_ALARM_MINUTES*60)):
            led_ramp_to(0)
            sleep_start = 0
            with open('log.txt', mode='a+') as f:
                f.write(f"Turning off LED at: {actual_time}")
    # Dawn/Dusk Mode turn up/down if motion for first time or if it was already on
    elif ((actual_time[3], actual_time[4]) >= DAWN_START and (actual_time[3], actual_time[4]) < DAY_START) or (((actual_time[3], actual_time[4]) >= DUSK_START and (actual_time[3], actual_time[4]) < SLEEP_MODE_START)):
        if motion or led.duty() > 0:
            led_ramp_to(DAWN_DUSK_PCT)
    # Day Mode turn on to full if motion or automatically if it was already on
    elif (actual_time[3], actual_time[4]) >= DAY_START and (actual_time[3], actual_time[4]) < DUSK_START:
        if motion or led.duty() > 0:
            led_ramp_to(DAY_PCT)

