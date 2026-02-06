"""Input client for slow control.
Terminal to type in commands, the output of which are displayed
in the output client to prevent blocking.
"""

import argparse

import yaml

from sctcamsoft.camera_control_client import CameraControlClient

# Load configuration
parser = argparse.ArgumentParser()
parser.add_argument('config_file', help='Path to slow control config file')
parser.add_argument('commands_file', help='Path to slow control commands file')
args = parser.parse_args()

with open(args.config_file, 'r') as config_file:
    config = yaml.safe_load(config_file)
server_host = config['user_interface']['host']
server_port = config['user_interface']['input_port']
header_length = config['user_interface']['header_length']

with open(args.commands_file, 'r') as commands_file:
    commands = yaml.safe_load(commands_file)

sc_client = CameraControlClient(server_host, server_port,
                                None, header_length, commands)

# Start a terminal for user input
print("SCT Slow Control - Input")
print("\nStart of night sequence:")
print("startup: set monitoring and turn on fans")
print("power_on: turn on camera power")
print("power_on_no_hv: turn on camera power with HV off")
print("setup_network: set up the networking after the modules are on")
print("\nEnd of night sequence:")
print("shutdown: turn off power and fans at end of night")
print("\nOther commonly used commands:")
print("power_off: turn off camera power")
print("fans_on, fans_off: turn camera fans on/off")
print("\n")
# Identify self to server
while True:
    raw_user_input = input('> ')
    if raw_user_input in ['exit', 'q']:
        sc_client.close()
        break
    try:
        sc_client.send_command(raw_user_input)
    except (ValueError, IndexError) as e:
        print(e)
        continue
