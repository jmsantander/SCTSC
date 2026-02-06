"""Output client for slow control.
Terminal to display the output of commands corresponding to inputs
given in the input client to prevent blocking.
"""

import argparse
import socket

import yaml

from sctcamsoft.camera_control_client import CameraControlClient

# Load configuration
parser = argparse.ArgumentParser()
parser.add_argument('config_file', help='Path to slow control config file')
args = parser.parse_args()

with open(args.config_file, 'r') as config_file:
    config = yaml.safe_load(config_file)
server_host = config['user_interface']['host']
server_port = config['user_interface']['output_port']
header_length = config['user_interface']['header_length']

sc_client = CameraControlClient(server_host, None, server_port,
                              header_length, None)

# Start a terminal for user input
print("\nSCT Slow Control - Output")
while True:
    updates = sc_client.recv_updates()
    if updates is not None:
        for update in updates:
            print(f'{update.device}: {update.variable}: ', end='')
            for value in update.values:
                if value.id:
                    print(f'\n  {value.id}: {value.value} {update.unit}', end='')
                else:
                    print("{} {}".format(value.value, update.unit), end='')
            print('')
