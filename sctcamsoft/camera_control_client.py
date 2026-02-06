__all__ = ['SlowControlClient',]

import socket
import shlex

import sctcamsoft.camera_control_pb2 as cc

class CameraControlClient():
    """Performs lowest-level socket communication with Camera server.

    A CameraControlClient instance accepts information on how to connect to the
    Camera Server. It manages the socket connections required for communication.
    
    An instance can operate as a simplex reciever or transmitter by providing
    only one of (server_input_port, server_output_port) to the constructor.
    If both are provided, full-duplex communciation is enabled. The "mode" of 
    the client can be tested with the `can_send()` and `can_recieve()` methods.

    Once the client becomes disconnected, or `close()` is called, the instance
    should be discarded. To attempt to reconnect to the server, a new instance
    should be created. 

    Note: The Camera server uses two seperate sockets for input and output. 
    Commands are sent via one, and updates are broadcast to all connected
    clients by the second.
    """

    def __init__(self, host, server_input_port, 
                server_output_port, header_length, 
                commands):
        """Creates a camera control client and connects to the server.
        
        Args: 
            host: The address of the server.
            server_input_port: The port exposed on the server which allocates
                sockets that accept Camera server commands.
            server_output_port: The port exposed on the server which allocates
                sockets that broadcast all Camera updates.
            header_length: The byte width of the header bytes prepended to
                each command and update.
            commands: A dict of all available server commands, used for
                command validation and formatting.
        """

        self._server_host = host
        self._server_input_port = server_input_port
        self._server_output_port = server_output_port
        self._header_length = header_length
        self._commands = commands

        self._send_cmd_sock = None
        self._recv_msg_sock = None
        self._connect_sockets()

    def _connect_sockets(self):
        if self._server_input_port is not None:
            self._send_cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._send_cmd_sock.connect((self._server_host, self._server_input_port))

        if self._server_output_port is not None:
            self._recv_msg_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._recv_msg_sock.connect((self._server_host, self._server_output_port))
            self._recv_msg_sock.setblocking(False)

    def _parse_and_serialize_command(self, cmd_string):
        raw_user_input = shlex.split(cmd_string.strip())
        command = raw_user_input[0]
        user_input = raw_user_input[1:]

        if command not in self._commands:
            raise ValueError("command '{}' not recognized".format(command))

        args = self._commands[command].get('args', {})
        unspecified_args = [a for a in args if args[a] is None 
                or isinstance(a, dict) and args[a].get('value') is None]

        if len(user_input) == len(args):
            user_args = args
        elif len(user_input) == len(unspecified_args):
            user_args = unspecified_args
        else:
            raise IndexError("command '{}' requires {} arguments, {} given".format(
                command, len(args), len(user_input)))
                
        message = cc.UserCommand()
        message.command = command
        for user_arg, input_value in zip(user_args, user_input):
            message.args[user_arg] = input_value
        serialized_message = message.SerializeToString()
        header = "{{:0{}d}}".format(self._header_length).format(len(serialized_message))

        return header.encode() + serialized_message

    def can_send(self):
        """Indicates whether this client is configured to send commands."""

        return (self._server_input_port is not None 
                and self._commands is not None
                and self._send_cmd_sock is not None)

    def can_receive(self):
        """Indicates whether this client is configured to recieve updates."""

        return (self._server_output_port is not None
                and self._recv_msg_sock is not None)

    def close(self):
        """Manually closes any open sockets.""" 

        if self._recv_msg_sock is not None:
            self._recv_msg_sock.close()
        if self._send_cmd_sock is not None:
            self._send_cmd_sock.close()

    def send_command(self, cmd_string):
        """Sends a command to the server.

        Args:
            cmd_string: The command to send. This string should be formatted
                as though it were typed directly into the `user_input.py`
                terminal. It will be shlex'd and parameters will be extracted
                according to the command definition in the commands dict
                provided to the client's constructor.
        """
        if not self.can_send():
            raise RuntimeError('SC client is not configured to send, '
                               'yet a send method was called.')

        message = self._parse_and_serialize_command(cmd_string)
        self._send_cmd_sock.sendall(message)

    def recv_updates(self):
        """Imeadiately returns server updates if any are available.

        If this client is configured to recieve messages, this method will 
        check if data is waiting on the recieving socket, read it, and create
        a protobuf UserUpdate object to return. The `updates` field of the
        UserUpdate is returned. That is, an array of protobuf "Update" objects.

        Returns:
            A list of protobuf Update objects, or None.
        """
        if not self.can_receive():
            raise RuntimeError('SC client is not configured to receive, '
                               'yet a receive method was called.')

        try: 
            header = self._recv_msg_sock.recv(self._header_length)
        except socket.error as e:
            return None
        
        if header:
            serialized_message = self._recv_msg_sock.recv(int(header))
            if serialized_message:
                user_update = cc.UserUpdate()
                user_update.ParseFromString(serialized_message)
                return user_update.updates
                
        return None
