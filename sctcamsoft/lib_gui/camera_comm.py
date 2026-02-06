import socket
import time
import logging

from sctcamsoft.camera_control_client import CameraControlClient
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

class CameraComm(QObject):
    """Wraps CameraControlClient for use in a PyQt architecture.

    The CameraComm is a worker QObject that uses CameraControlClient to
    implement low-level camera communication, including command sending,
    update receiving, connection state tracking, and connection retry.

    Attributes:
        CONNECT_RETRY_INTERVAL: Time interval to wait after failing to send or 
            recieve before attempting to reconnect to the server.
        on_connec_state_changed: A pyqt signal emitted when the client
            connects or disconnects.
        on_update: A pyqt signal emitted for each received update. The
            argument is a protobuf Update object. 
        on_bad_command: A pyqt signal emitted when a malformed command is
            passed to `send_command()`.
    """

    CONNECT_RETRY_INTERVAL = 5 # seconds

    on_connec_state_changed = pyqtSignal(bool)
    on_update = pyqtSignal(object)
    on_bad_command = pyqtSignal(str, str)

    def __init__(self, host, server_input_port, 
                 server_output_port, header_length, commands):
        """Accept and store variables required for a client.

        See CameraControlClient's constructor for documentation of arguments.

        This worker object is meant to be moved to a QThread, because the 
        connection retry logic blocks until the connection attempt 
        is successful.

        Note, unlike in CameraControlClient, this method does not connect 
        to the camera immeadiately. To connect, you must call `init()`.
        """

        QObject.__init__(self)

        logging.debug('Instantiating the camera communication object.')
    
        self._host = host
        self._server_input_port = server_input_port
        self._server_output_port = server_output_port
        self._header_length = header_length
        self._commands = commands

        self._is_connected = False
        self._camera_client = None

    def init(self): 
        """Attempt to connect to the camera, then start checking for updates.

        Begin a connection attempt loop. This method will block until
        the client successfully connects to the server.

        Once the client is connected, a repeating update check is scheduled.
        If that update check fails, the connection is destroyed and the 
        reconnect loop is restarted.
        """
        logging.debug('Configuring camera to connect and begin polling.')

        # Once the event loop is started, attempt to connect
        QTimer.singleShot(0, self._attempt_until_connected)

        # Then, set up a timer that will poll the server for update 
        self._communicate_timer = QTimer()
        self._communicate_timer.timeout.connect(self._check_for_updates)
        self._communicate_timer.start(0)

    @pyqtSlot(str)
    def send_command(self, command):
        """Send a command to the server.

        If the command sending fails, a reconnect loop is started.
        
        Args:
            command: The string command to send to the server. The command
                should be formatted as though it were being typed into the
                user_input.py terminal.
        """

        self._send_recv_wrapper(self._send_func, command)

    # TODO: In the future, this should be implemented as
    # a heartbeat from the server - some kind of update
    # sent by the server at a regular (1 Hz?) interval.
    def is_connected(self):
        """Return this client's connected state.
        
        Note, the connection state is only updated if the server intentionally 
        closes this connection, or if a send_command attempt fails.
        """
        return self._is_connected

    def _attempt_connect(self):
        try:
            if self._camera_client != None:
                self._camera_client.close_recv()
        except:
            logging.warning('Failed to close recieving socket.')

        try:
            if self._camera_client != None:
                self._camera_client.close_send()
        except:
            logging.warning('Failed to close sending socket.')

        logging.debug(
                'Attempting to connect to %s at input port %d and output port %d.', 
                self._host, self._server_input_port, self._server_output_port)

        try:
            self._camera_client = CameraControlClient(
                self._host, self._server_input_port, 
                self._server_output_port, self._header_length, 
                self._commands)
        except Exception as ex:
            logging.warning('Error attempting to connect to the server.')
            self._set_connected(False)
            raise

        logging.info('Successfully connected to the camera server')
        self._set_connected(True)

    def _attempt_until_connected(self):
        retry_count = 0
        while not self._is_connected: 
            try:
                self._attempt_connect()
            except Exception as ex:
                retry_count = retry_count + 1
                logging.info(
                    'Retrying failed connection attempt (%d) in %d seconds.', 
                    retry_count, self.CONNECT_RETRY_INTERVAL)
                time.sleep(self.CONNECT_RETRY_INTERVAL)

    def _check_for_updates(self):
        self._send_recv_wrapper(self._recv_func)

    def _send_recv_wrapper(self, send_recv_func, *args, **kwargs):
        """Logic applicable to sending and recieving functions.
        
        This is an outer (wrapper) function that includes error 
        catching and retry logic used for both server sends 
        and recieves.
        """
        try:
            send_recv_func(*args, **kwargs)
        
        # If there is an error in sending commands or recieving updates,
        # notify slots that the connection is broken and start the 
        # reconnect loop
        except (socket.error, ConnectionError):
            logging.exception('Error communicating with the camera.')
            logging.info('Destroying connection, will attempt to reconnect.')
            self._set_connected(False)
            self._attempt_until_connected()

    def _send_func(self, command):
        try: 
            self._camera_client.send_command(command)

        # TODO: Create custom exceptions for each of 
        # these in camera_control_client
        except ValueError as err:
            message = 'Error in send_command, command not recognized.'
            logging.exception(message)
            self.on_bad_command.emit(message, command)
        except IndexError as err:
            message = 'Error in send_command, command submitted with incorrect arguments.'
            logging.exception(message)
            self.on_bad_command.emit(message, command)

    def _recv_func(self):
        """Receive updates and propagate them to on_update signal.
        
        Receive any updates broadcast by the server and emit the on_update
        signal for each Update object recieved from the server.

        This method is called on loop once this client is `init`'d.
        """
        updates = self._camera_client.recv_updates()
        if updates is not None:
            for update in updates:
                logging.debug(('Update recieved from server. Emitting signal '
                    'with the following object:\n%r'), update)
                self.on_update.emit(update)

    def _set_connected(self, new_status):
        prev_status = self._is_connected
        self._is_connected = new_status

        # If the connection state has changed, emit state update
        if self._is_connected != prev_status:
            self.on_connec_state_changed.emit(self._is_connected)
