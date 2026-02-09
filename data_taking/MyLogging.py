import os,sys
import logging
from colorlog import ColoredFormatter
import warnings

stdout_fd = sys.stdout.fileno()
stderr_fd = sys.stderr.fileno()


def redirect_stdout(logfile='/dev/null'):
    sys.stdout.flush()
    local_stdout = os.dup(stdout_fd)
    fileout = os.open(logfile, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    os.dup2(fileout,stdout_fd)
    os.close(fileout)
    sys.stdout = os.fdopen(local_stdout,'w')

def redirect_stderr(logfile='/dev/null'):
    sys.stderr.flush()
    local_stderr = os.dup(stderr_fd)
    fileout = os.open(logfile, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    os.dup2(fileout,stderr_fd)
    os.close(fileout)
    sys.stderr = os.fdopen(local_stderr,'w')


class LoggerWriter(logging.getLoggerClass()):
    TEST_LEVEL_INFO = 100
    TEST_LEVEL_MESS = 110
    TEST_LEVEL_PASS = 120
    TEST_LEVEL_WARNING = 125
    TEST_LEVEL_FAIL = 130
    def __init__(self, logname=None,logfile=None):
        super(LoggerWriter,self).__init__(logname,level=logging.NOTSET)
        self.stdout_stderr_already_redirected = False
        logging.addLevelName(self.TEST_LEVEL_INFO, "TEST_INFO")
        logging.addLevelName(self.TEST_LEVEL_MESS, "TEST_INFO") ## MESS
        logging.addLevelName(self.TEST_LEVEL_PASS, "TEST_PASS")
        logging.addLevelName(self.TEST_LEVEL_WARNING, "TEST_WARNING")
        logging.addLevelName(self.TEST_LEVEL_FAIL, "TEST_FAIL")

        if logname is not None and logfile is not None:
            self.setup(logname=logname,logfile=logfile)

    def redirect_warnings(self):
        def customwarn(message, category, filename, lineno, file=None, line=None):
            self.warning(warnings.formatwarning(message, category, filename, lineno))
        warnings.showwarning = customwarn

    def setup(self,logname='mylog',logfile='mylog.log', debug_mode = False):
        self.name = logname
        self.redirect_warnings()
        if not debug_mode and not self.stdout_stderr_already_redirected:
            redirect_stdout(logfile=logfile)
            redirect_stderr(logfile=logfile)
            self.stdout_stderr_already_redirected = True

        self.stdout_handler = logging.StreamHandler(sys.stdout)
        #self.stderr_handler = logging.StreamHandler(sys.stderr)
        if debug_mode:
            self.stdout_handler.setLevel(logging.DEBUG)
            #self.stderr_handler.setLevel(logging.DEBUG)
        else:
            self.stdout_handler.setLevel(self.TEST_LEVEL_INFO)
            #self.stderr_handler.setLevel(self.TEST_LEVEL_INFO)
        self.file_handler = logging.FileHandler(logfile)
        self.file_handler.setLevel(logging.DEBUG)
        
        self.formatter = logging.Formatter('%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        #self.console_formatter = ColoredFormatter("%(log_color)s %(levelname)-8s%(reset)s %(blue)s%(message)s",
        self.console_formatter = ColoredFormatter("%(log_color)s%(asctime)s - %(name)-15s - %(levelname)-8s - %(message)s%(reset)s",
	  datefmt='%Y-%m-%d %H:%M:%S',
	  reset=True,
	  log_colors={
		'DEBUG':    'white',
		'INFO':     'blue',
		'WARNING':  'yellow',
		'ERROR':    'red',
		'CRITICAL': 'red',
                'TEST_INFO': 'blue',
                'TEST_PASS': 'green',
                'TEST_FAIL': 'red',
                'TEST_MESS': 'cyan',
                'TEST_WARNING': 'yellow'
	  },
	  secondary_log_colors={
#          'DEBUG':    'white',
#          'INFO':     'blue',
#          'WARNING':  'yellow',
#          'ERROR':    'red',
#          'CRITICAL': 'red'

          },
	  style='%'
          )


        self.file_handler.setFormatter(self.formatter)
        self.stdout_handler.setFormatter(self.console_formatter)
        #self.stderr_handler.setFormatter(self.console_formatter)

        self.handlers.clear()

        self.addHandler(self.file_handler)
        self.addHandler(self.stdout_handler)
        #self.addHandler(self.stderr_handler)


logger = LoggerWriter()#'mylog','mylog.log')
#def init_logger(logfile):
#    global logger
#    logger = LoggerWriter(logfile=unique_filename(logfile))
