#!/data/software/anaconda2/envs/sctcamsoft/bin/python

# write_confluence_log.py
# Ari Brill 10/3/19
# From a run log in compressed format and user input,
# write a text file suitable for posting to the Confluence
# TARGET electronic log.
# Parse both data runs and rate scans.

import datetime
import os
import pickle

from astroplan import Observer
from astropy.coordinates import get_moon
from astropy.utils import iers
import numpy as np

from run_info import get_saved_run_info, get_livetime, get_rate_scan_results

# Disable automatic updating of IERS tables
iers.conf.auto_download = False

RUN_LOG_FILE = "/home/ctauser/run_log.pkl"
OUTPUT_DIR = "/data/logs/"
TEMPERATURE_DIR = "/data/local_outputDir"
# Current all modules - central module 110 is omitted
ALL_MODULES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 103, 106, 107, 108, 111, 112,
               114, 115, 119, 121, 123, 124, 125, 126]
STANDARD_NUM_BLOCKS = 4
STANDARD_TRIGGER_DELAY = 668
TEMPERATURE_LOWER_LIMIT = 4  # degrees C - to ignore broken sensors
TEMPERATURE_UPPER_LIMIT = 125  # degrees C - to ignore broken sensors

# Convert pickle from Python 2 into Python 3
def convert(data):
    if isinstance(data, bytes):
        return data.decode('ascii')
    if isinstance(data, dict):
        return dict(map(convert, data.items()))
    if isinstance(data, tuple):
        return map(convert, data)
    return data

# Load the run log from the compressed file, keeping only recent runs
def load_recent_runs(run_log_file):
    run_info = get_saved_run_info()
    night_start = datetime.datetime.fromisoformat(run_info['night_start'])
    with open(run_log_file, 'rb') as logfile:
        while True:
            try:
                run = pickle.load(logfile, encoding='bytes')
                run = convert(run)
                try:
                    if run['run_timestamp'] < night_start:
                        continue
                    yield run
                except:
                    if run['timestamp'] < night_start:
                        continue
                    yield run
            except EOFError:
                break

def get_module_string(modules):
    if modules is None or None in modules or set(modules) - set(ALL_MODULES):
        return "invalid module selection"
    absent_modules = set(ALL_MODULES) - set(modules)
    if set(modules) == set(ALL_MODULES):
        string = 'all modules'
    elif not modules:
        string = 'no modules'
    elif len(modules) == 1:
        string = 'module {}'.format(modules[0])
    elif len(modules) == 2:
        string = 'modules {} and {}'.format(modules[0], modules[1])
    elif len(absent_modules) <= 4:
        modules_string = ', '.join([str(i) for i in absent_modules])
        string = 'all modules but ' + modules_string
    else:
        string = 'modules ' + ', '.join([str(i) for i in modules])
    return string

def get_sky_string(timestamp):
    flwo = Observer.at_site('flwo', timezone='US/Arizona')
    run_time = flwo.datetime_to_astropy_time(timestamp)
    is_night = flwo.is_night(run_time)
    moon_up = flwo.target_is_up(run_time, get_moon(run_time))
    if not is_night:
        string = 'daytime'
    elif moon_up:
        moon_illumination = flwo.moon_illumination(run_time)
        moon_percent = "{:.2f}%".format(moon_illumination * 100)
        string = moon_percent + ' moon'
    else:
        string = ''
    return string

def get_fee_temperature_string(run_id):
    filename = "{}_temperatures.txt".format(run_id)
    temperature_file = os.path.join(TEMPERATURE_DIR, filename)
    if not os.path.exists(temperature_file):
        string = "(no temperature file found)"
        return string
    # Keep only the temperatures, discarding the module IDs and timestamps
    with open(temperature_file, 'r') as tf:
        num_cols = len(tf.readline().strip().split(','))
    usecols = range(2, num_cols)
    temps = np.loadtxt(temperature_file, delimiter=',', usecols=usecols,
                       skiprows=1)
    temps = temps.flatten()
    # Discard outliers from broken sensors
    temps = temps[(temps > TEMPERATURE_LOWER_LIMIT) &
                  (temps < TEMPERATURE_UPPER_LIMIT)]
    try:
        string = "{:.2f} C avg / {:.2f} C min / {:.2f} C max".format(
            np.mean(temps), np.min(temps), np.max(temps))
    except ValueError:
        string = "(no data from working temperature sensors)"
    return string

# Load the recent runs
recent_runs = load_recent_runs(RUN_LOG_FILE)

# Write logging info to output file
today = datetime.date.today()
output_file = os.path.join(OUTPUT_DIR, today.isoformat() + '_log.txt')
print("** Writing run log **")
with open(output_file, 'w') as f:
    for run in recent_runs:
        utc_time = run['run_timestamp']
        utc_time_string = str(utc_time)
        # Convert UTC to local time manually.
        # We have to do this because the camera server is set to Central Time,
        # and it's possible to do this because Arizona has no Daylight Savings.
        local_time = run['run_timestamp'].replace(
            tzinfo=datetime.timezone.utc).astimezone(
                tz=datetime.timezone(
                    datetime.timedelta(hours=-7), name='America/Phoenix'))
        local_time_string = local_time.strftime("%H:%M:%S")
        # Run header
        runstr = {'data_run': 'Run', 'rate_scan': 'Rate Scan'}
        header = "* {} {} at {} UTC ({} local)".format(runstr[run['run_type']],
                                                       run['run_id'],
                                                       utc_time_string,
                                                       local_time_string)
        f.write(header + '\n')
        backplane = "** Backplane clock started at {} UTC".format(run['origin_timestamp'])
        f.write(backplane + '\n')
        print(header[2:])
        # Modules info
        module_string = get_module_string(run['modules'])
        trigger_string = get_module_string(run['trigger_modules'])
        line = '** ' + module_string + '; triggering on ' + trigger_string
        line += '\n'
        f.write(line)
        if run['failed_modules']:
            failure_string = get_module_string(run['failed_modules'])
            f.write("** failed to connect to " + failure_string + '\n')
        # Write list of suppressed pixels
        masked_pixels = {}
        for mod, pixels in run.get('masked_trigger_pixels', {}).items():
            pixstr = [str(pixel) for pixel in pixels]
            masked_pixels[int(mod)] = "({}: {})".format(mod, ', '.join(pixstr))
        mask_strings = []
        for module, mask_string in masked_pixels.items():
            if module in run['modules'] and module in run['trigger_modules']:
                mask_strings.append(mask_string)
        if mask_strings:
            line = '** masked trigger pixels ' + '; '.join(mask_strings) + '\n'
            f.write(line)
        # Write loaded tuning temps for each module
        #tuning_temps = {}
        tuning_temps_strings = []
        for mod, temp in run.get('loaded_tuning_temps', {}).items():
            #tuning_temps[int(mod)] = "({}: {})".format(mod, temp)
            tuning_temps_strings.append("({}: {})".format(mod, temp))
        if tuning_temps_strings:
            line = '** loaded tuning temps ' + '; '.join(tuning_temps_strings) + '\n'
            f.write(line)
        # Run info: target and observing conditions
        target_string = run['target_name']
        if run['shutter_open']:
            target_string += ", RA: {}, Dec: {}".format(run['ra'], run['dec'])
        shutter_status = 'open' if run['shutter_open'] else 'closed'
        hv_status = 'on' if run['HV_on'] else 'off'
        line = "** target: {} (shutter {}, HV {})".format(target_string,
                                                          shutter_status,
                                                          hv_status)
        sky_string = get_sky_string(local_time)
        if sky_string:
            line += ', ' + sky_string
        f.write(line + '\n')
        # Flasher info (if applicable)
        if run['flasher_on']:
            for flasher, LED in [('top', run['top_flasher_LED']),
                                 ('middle', run['middle_flasher_LED']),
                                 ('bottom', run['bottom_flasher_LED'])]:
                if LED != '0000000000':
                    line = "** {} flasher on at ".format(flasher)
                    line += "{} Hz with LED pattern {}\n".format(
                        run['flasher_rate'], LED)
                    f.write(line)
        # Temperature info
        fee_temps = get_fee_temperature_string(run['run_id'])
        line = '** chiller '
        line += 'on' if run['chiller_on'] else 'off'
        line += ', fans '
        line += 'on' if run['fans_on'] else 'off'
        line += ", FEEs at {}\n".format(fee_temps)
        f.write(line)
        # Data run only
        if run['run_type'] == 'data_run':
            # Run settings
            duration = str(datetime.timedelta(seconds=run['set_duration']))
            livetime = get_livetime(run['run_id'], run['set_duration'])
            pretty_livetime = str(datetime.timedelta(seconds=livetime))
            if len(set(run['threshold_us'])) == 1:
                threshold_us = str(run['threshold_us'][0]) + ' US DAC thresh'
            else:
                threshold_us = ', '.join([str(i) for i in run['threshold_us']])
                threshold_us += ' US DAC thresh'
            if len(set(run['threshold_infn'])) == 1:
                threshold_infn = str(run['threshold_infn'][0]) + ' INFN DAC thresh'
            else:
                threshold_infn = ', '.join([str(i) for i in run['threshold_infn']])
                threshold_infn += ' INFN DAC thresh'
            line = "** {} (~{} livetime), {}, {}".format(duration, pretty_livetime,
                                                     threshold_us, threshold_infn)
            if run['num_blocks'] != STANDARD_NUM_BLOCKS:
                line += ', {} blocks'.format(run['num_blocks'])
            if run['trigger_delay'] != STANDARD_TRIGGER_DELAY:
                line += ', trigger delay {}'.format(run['trigger_delay'])
            line += '\n'
            f.write(line)
            # Run results
            num_packets_lost = (run['num_packets_expected']
                                - run['num_packets_received'])
            if livetime > 0:
                approximate_rate = "{0:.1f}".format(run['num_events'] / livetime)
            else:
                approximate_rate = 0
            line = "** {} packets received ({} lost) \
                    in {} events (~{} Hz rate)\n".format(
                        run['num_packets_received'], num_packets_lost,
                        run['num_events'], approximate_rate)
            f.write(line)
        # Rate scan only
        elif run['run_type'] == 'rate_scan':
            # Scan settings
            line = '** thresholds scanned from '
            line += str(max(run['pe_thresholds']))
            line += ' to '
            line += str(min(run['pe_thresholds']))
            line += ' DAC\n'
            f.write(line)
            # Scan results
            flasher_rate = run['flasher_rate'] if run['flasher_on'] else 0
            scan_results = get_rate_scan_results(run['run_id'],
                                                 flasher_rate=flasher_rate)
            f.write(scan_results + '\n')
        f.write('\n')

print("Done! Output saved to {}.".format(output_file))
print("Press Ctrl-Shift-D when editing the TARGET Electronic Log in Confluence")
print("to open Markdown mode, and copy-paste the file contents there.")
print("Add any additional comments as needed.")
