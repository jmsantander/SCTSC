import argparse
from datetime import datetime
import os
import time

from opcua import Client

#Hey, here is some ugly stuff to setup IP for drive PLC:
if "DRIVE_PLC_IP" in os.environ:
    DRIVE_PLC_IP = os.getenv('DRIVE_PLC_IP')
else:
    DRIVE_PLC_IP = "172.17.3.3"

# opcua client to get current pointing
def get_opcua_coord_children():
    #plc = "172.17.3.3"      # pSCT
    client = Client("opc.tcp://" + DRIVE_PLC_IP + ":4840/Objects/Logic/")
    client.connect()
    root = client.get_root_node()
    objPLC=root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA"])
    RA_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_RA"])
    Dec_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_Dec"])
    timestamp_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_time"])
    timeDT_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_Time_DT"])
    az_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_position", "2:az"])
    el_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_position", "2:el"])
    nominal_az_child = root.get_child(
        ["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_nominal_position", "2:az"])
    nominal_el_child = root.get_child(
        ["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", "2:current_nominal_position", "2:el"])
    return client, objPLC, timestamp_child, timeDT_child, az_child, el_child, nominal_az_child, nominal_el_child, RA_child, Dec_child


# opcua client to get current pointing
def get_opcua_children_list(childrenlist=["current_RA", "current_Dec", "current_time", "current_Time_DT",
                                          ["current_position", "az"], ["current_position", "el"],
                                          ["current_nominal_position", "az"], ["current_nominal_position", "el"],
                                          ]):
    #plc = "172.17.3.3"      # pSCT
    client = Client("opc.tcp://" + DRIVE_PLC_IP + ":4840/Objects/Logic/")
    client.connect()
    root = client.get_root_node()
    objPLC=root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA"])
    return_childrenlist = []
    for child_ in childrenlist:
        #print("getting node for {}".format(child_))
        if type(child_) is list:
            this_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA"] + child_ )
        else:
            this_child = root.get_child(["0:Objects", "2:Logic", "2:Application", "2:UserVarGlobal_OPCUA", child_])
        return_childrenlist.append(this_child)

    return client, objPLC, return_childrenlist

def query_tracking(interval=5, outfile=None,
                   childrenlist=["current_time", "current_Time_DT",
                                 ["current_position", "az"], ["current_position", "el"],
                                 ["current_nominal_position", "az"], ["current_nominal_position", "el"],
                                 "current_RA", "current_Dec",
                                 "is_moving", "is_off", "is_on_source", "is_tracking",
                                 ["current_tracking_error", "pos", "az"], ["current_tracking_error", "pos", "el"],
                                 ["current_tracking_error", "t"],
                                ]
                    ):
    try:
        plc_client, objPLC, return_childrenlist = get_opcua_children_list(childrenlist)
        outnames = []
        for childname in childrenlist:
            if type(childname) is list:
                outnames.append("_".join(childname))
            else:
                outnames.append(childname)
        if outfile is not None:
            if os.path.exists(outfile):
                append_write = 'a'  # append if already exists
            else:
                append_write = 'w'  # make a new file if not
            outf = open(outfile, 'a')
            print("Saving results to output file {}".format(outfile))
            if append_write == 'w':
                outf.write(",".join(outnames)+"\n")
        if interval != 0:
            print(",".join(outnames)+"\n")

        i = 0
        while True:
            outvals = []
            for childname, childnode in zip(outnames, return_childrenlist):
                #print(childname+", "),
                val_ = childnode.get_value()
                if childname == "current_RA":
                    val_ = val_ * 15.
                elif childname == "current_time":
                    #print(val_)
                    val_ = datetime.fromtimestamp(val_ / 1.e3)
                if type(val_) is float:
                    val_ = round(val_, 6)
                #print(val_)
                outvals.append(val_)

            if i==10:
                print(",".join(outnames) + "\n")
                i=0
            i = i+1
            if outfile is not None:
                outf.write(",".join(map(str, outvals)) + "\n")

            # If no interval provided, return the values
            if interval == 0:
                return outnames, outvals

            # Otherwise print to screen and repeat in a loop
            print(",".join(map(str, outvals)) + "\n")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("Measurement stopped by user. ")
        pass
    finally:
        if interval != 0:
            print("Stopping tracking acquisition. ")
        plc_client.disconnect()
        if outfile is not None:
            outf.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start tracking acquisition from the drive system PLC server, '
                                                 'and (optionally) dump to file. '
                                                 'Note that the UTC from drive system PLC server is ~2 s earlier than the timestamp (with ms precision, which I use to convert to local time), unclear why. '
                                                 'Stop the script by ctrl-c.  ')
    now = datetime.now()
    now = now.strftime("%Y%m%d_%H%M%S")
    outfile = "/data/logs/positioner_logs/positionerLog_" + now + ".txt"
    parser.add_argument('-i', '--interval', default=5, type=float, help='Interval (s) between queries. Default is 5 s.')
    parser.add_argument('-o', '--outfile', default=outfile, help='Create a local file to save tracking info. Default saves to /data/logs/positioner_logs/. ')

    args = parser.parse_args()

    print('Starting to query tracking every {} s, until a stop, ctrl-c, is received.'.format(args.interval))
    query_tracking(interval=args.interval, outfile=args.outfile)

