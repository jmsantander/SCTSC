import itertools
import os

import numpy as np
import yaml

import record_tracking

def prompt_user(prompt, options, default):
    input_prompt = prompt
    if default is not None:
        # Show all options marking the default if there aren't too many options
        if options is not None and len(options) <= 5:
            display_options = ['[{}]'.format(option) if option == default
                               else str(option) for option in options]
            input_prompt += ' (' + '/'.join(display_options) + '): '
        # Otherwise just show the default
        else:
            input_prompt += ' [{}]: '.format(default)
    user_input = input(input_prompt)
    if not user_input:
        user_input = default
    if options is not None and user_input not in options:
        print("{} is not a valid input".format(user_input))
        user_input = prompt_user(prompt, options, default)
    return user_input

def prompt_yesno(prompt, default=False):
    default = 'y' if default else 'N'
    user_input = prompt_user(prompt, ['y', 'N'], default)
    truth = {'y': True, 'N': False}
    return truth[user_input]

def prompt_flasher_info(rate_default=10, top_default='0000000000',
                        middle_default='0000000000',
                        bottom_default='0000000000'):
    options = [''.join(i) for i in itertools.product(['0', '1'], repeat=10)]
    top_leds = prompt_user("Top flasher LEDs?", options, top_default)
    middle_leds = prompt_user("Middle flasher LEDs?", options, middle_default)
    bottom_leds = prompt_user("Bottom flasher LEDs?", options, bottom_default)
    rate = prompt_user("Flasher rate [Hz]?", None, rate_default)
    return rate, top_leds, middle_leds, bottom_leds

def print_run_info(run_info):
    print("\n    *** Run settings ***")
    print("Chiller:                {}".format('<ON>' if run_info['chiller_on']
                                              else ' off'))
    print("Fans:                   {}".format('<ON>' if run_info['fans_on']
                                              else ' off'))
    print("Shutter:                {}".format('<OPEN>'
                                              if run_info['shutter_open']
                                              else ' closed'))
    if run_info['shutter_open']:
        print("Right ascension:         {0:.4f}".format(run_info['ra']))
        print("Declination:             {0:.4f}".format(run_info['dec']))
        print("Target name:             {}".format(run_info['target_name']))
    print("Flasher:                {}".format('<ON>' if run_info['flasher_on']
                                              else ' off'))
    if run_info['flasher_on']:
        print("Flasher rate:           {}".format(run_info['flasher_rate']))
        print("Top flasher LEDs:       {}".format(
            run_info['top_flasher_LED']))
        print("Middle flasher LEDs:    {}".format(
            run_info['middle_flasher_LED']))
        print("Bottom flasher LEDs:    {}".format(
            run_info['bottom_flasher_LED']))

def get_ra_dec():
    query = {"current_RA": None, "current_Dec": None}
    outnames, outvals = record_tracking.query_tracking(interval=0)
    for name, val in zip(outnames, outvals):
        if name in query:
            query[name] = val
    return tuple(query.values())

def get_saved_run_info():
    # Load saved run info
    run_info_file = '.run_info.yml'
    with open(run_info_file, 'r') as runfile:
        run_info = yaml.safe_load(runfile)
    return run_info

def save_run_info(run_info):
    with open('.run_info.yml', 'w') as run_info_file:
        yaml.dump(run_info, run_info_file, default_flow_style=False)

def get_run_info():

    # Display the saved run info to the user
    run_info = get_saved_run_info()
    print("\nPreparing run {} of the night...".format(
        run_info['num_night_runs'] + 1))
    print_run_info(run_info)

    # If the settings need to be changed, prompt for new settings
    good_settings = prompt_yesno("Settings correct for the current run?")
    if not good_settings:
        print("\nEnter information about the run:")
        run_info['chiller_on'] = prompt_yesno("Chiller on?",
                                              run_info['chiller_on'])
        run_info['fans_on'] = prompt_yesno("Fans on?", run_info['fans_on'])
        run_info['shutter_open'] = prompt_yesno("Shutter open?",
                                                run_info['shutter_open'])
        if run_info['shutter_open']:
            ra, dec = get_ra_dec()
            run_info['ra'] = ra
            run_info['dec'] = dec
            print("Present coordinates: RA: {}, Dec: {}".format(ra, dec))
            default = run_info['target_name']
            if default == "NOSOURCE":
                default = "NONE"
            run_info['target_name'] = prompt_user("Target", None, default)
        else:
            run_info['target_name'] = "NOSOURCE"
        run_info['flasher_on'] = prompt_yesno("Flasher on?",
                                              run_info['flasher_on'])
        if run_info['flasher_on']:
            (run_info['flasher_rate'],
             run_info['top_flasher_LED'],
             run_info['middle_flasher_LED'],
             run_info['bottom_flasher_LED']) = prompt_flasher_info(
                 run_info['flasher_rate'],
                 run_info['top_flasher_LED'],
                 run_info['middle_flasher_LED'],
                 run_info['bottom_flasher_LED'])
        # Display the new run info
        print_run_info(run_info)

    # Save the run info so it will be the default for the next run
    run_info['num_night_runs'] += 1
    save_run_info(run_info)

    # Return run info for logging
    return run_info

def get_livetime(run_id, duration, output_directory="/data/local_outputDir/"):
    """
    Return the livetime estimated by subtracting
    the deadtime due to ADC readings from the run duration.
    """
    # Use the timestamps from the first available output file
    # They're the overall times, so the same regardless of the output used
    for adc_output in ['temperatures', 'currents']:
        filename = "{}_{}.txt".format(run_id, adc_output)
        filepath = os.path.join(output_directory, filename)
        try:
            timestamps = np.loadtxt(filepath, delimiter=',', usecols=(0, 1),
                                    skiprows=1, dtype=np.datetime64)
            timestamps = np.atleast_2d(timestamps)
        except OSError:
            continue
        deadtimes = timestamps[:, 1] - timestamps[:, 0]
        total_deadtime = np.sum(deadtimes) / np.timedelta64(1, 's')
        livetime = duration - total_deadtime
        return livetime
    # No output files, so there was no deadtime
    return duration

def get_rate_scan_results(run_id, desired_rate=10, flasher_rate=0,
                          rate_baseline=0):
    """
    Calculate the results of a rate scan from the output file.
    Detect either a threshold value or plateau of values
    matching the desired rate in Hz. Default rate: 10 Hz.
    Optionally detect a total rate of the desired rate plus flasher rate.
    Subtract off the constant baseline rate from hitmap reading in DAC.
    This is 9.6 DAC for the current code and 4.8 for the old code.
    Return a string to print stating the results.
    QF: changed default rate baseline to 0, 
    as the RateScanner now subtract the TACK messages for trigger hitmaps
    """
    rate_scan_dir = "/data/local_outputDir/"
    rate_scan_path = os.path.join(rate_scan_dir, "{}_scan.txt".format(run_id))
    results = np.loadtxt(rate_scan_path)
    thresholds = results[:, 0]
    rates = results[:, 1]
    # Subtract off baseline rate from DACQ
    rates -= rate_baseline
    # Detect the total rate, including the flasher rate (if any)
    desired_rate = float(desired_rate)
    desired_rate += float(flasher_rate)
    # Detect a single threshold triggering at the desired rate (default: 10 Hz)
    # Flip because np.interp requires the sequence to be increasing
    rate_threshold = np.interp(desired_rate, np.flip(rates),
                               np.flip(thresholds))
    #log_rate_threshold = np.interp(np.log10(desired_rate), np.flip(np.log10(rates)),
    #                           np.flip(thresholds))
    #print(rate_threshold, log_rate_threshold)
    # Detect a plateau of thresholds all triggering at the fiducial rate
    # We only care about plateaus in the center of the scanned range -
    # the extremes are irrelevant
    good = (rates > 1) & (rates < 500)
    # Look for adjacent points that are about the same
    flat = np.abs(np.diff(rates[good])) < 1
    # If there is a plateau, report it
    if True in flat:
        # Include the last endpoint of the plateau, too (if there is one)
        flat_endpoint = np.concatenate([flat, np.array([False])])
        for i in range(1, len(flat_endpoint)):
            if flat[i - 1]:
                flat_endpoint[i] = True
        plateau = thresholds[good][flat_endpoint]
        rate_plateau = rates[good][flat_endpoint]
        string_plat = "** {} Hz plateau (subtracted baseline {:.1f} Hz) from about {} to {} DAC\n".format(
            int(np.mean(rate_plateau)),
            rate_baseline, 
            #int(desired_rate),
            int(np.max(plateau)),
            int(np.min(plateau)))
    else: 
        string_plat = ""
    # Otherwise, if a threshold with the required rate was found, report that
    # QF: deleted the "el" in elif, because the platau disregard the rate_thresh which is what we are interested in. 
    if (rate_threshold > np.min(thresholds) and
          rate_threshold < np.max(thresholds)):
        string = "** {} Hz rate (added flasher {} Hz) at about {} DAC".format(int(desired_rate),
        flasher_rate, 
                                                        int(rate_threshold))
    # Else, no good threshold was found
    else:
        #string = "** unable to detect {} Hz rate or plateau".format(
        string = "** unable to detect {} Hz rate".format(
            int(desired_rate))
    string = string_plat + string
    return string
