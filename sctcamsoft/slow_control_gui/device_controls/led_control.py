def led_control (command, led):
        if (command=='on'):
            led.value = True
        elif (command=='off'):
            led.value = False

