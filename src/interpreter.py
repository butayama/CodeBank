from .utils import SYSTEM, WINDOWS, TIDAL_BOOT_FILE, PYTHON_EXECUTABLE
import re, shlex, threading, tempfile, time, sys
from subprocess import Popen, TimeoutExpired
from subprocess import PIPE, STDOUT

CREATE_NO_WINDOW = 0x08000000 if SYSTEM == WINDOWS else 0

class Interpreter:
    prompt = ">>>"
    name = "Interpreter"
    name_short = None
    name_long = None
    ident = None
    def __init__(self, path, verbose=True):

        self.path = shlex.split(path)
        self.stdout = tempfile.TemporaryFile("w+", 1) # buffering = 1
        self.is_alive = True
        self.silent = not verbose

        self.streams = re.compile(self.__class__.re_streams)

        self._last_response = None
        self._thread_lock = threading.Lock()

        try:
        
            self.process = Popen(self.path, shell=False, universal_newlines=True, bufsize=1,
                              stdin=PIPE,
                              stdout=self.stdout,
                              stderr=self.stdout,
                              creationflags=CREATE_NO_WINDOW)

            self.stdout_thread = threading.Thread(target=self.read_stdout)
            self.stdout_thread.start()

        except FileNotFoundError:

            raise FileNotFoundError(self.path)

        self._banned_commands      = []
        self._unmonitored_commands = []

        self._colour_map = {}
        
        self.execute_setup_code()

    @classmethod
    def get_short_name(cls):
        return cls.name_short

    @classmethod
    def get_name(cls):
        return cls.name_long

    @classmethod
    def get_id(cls):
        return cls.ident

    def execute_setup_code(self):
        """ Called from __init__ - code required at startup e.g. imports """
        return

    def start_server(self):
        """ Executes any code necessary to allow clock sync """
        return

    def stop_server(self):
        """ Executes any code necessary to stop server functionality """
        return

    def sync_to_server(self, ip_address):
        """ If there is any required synchronisation with the server from the lang, do so here """
        return

    def format_code(self, string):
        """ Formats code specifically to an interpreter if necessary """
        return string

    def get_streams(self, string):
        """ Uses a RegEx to return the streams of audio present in a string of code """
        return self.streams.findall(string)

    def execute(self, code_string, verbose=True):
        """ Pipe string into interpreter """
        if code_string is not None:
            # Get thread control
            self._thread_lock.acquire()
            
            if verbose and not self.silent:
            
                self.print_to_console(code_string)
            
            self.pipe_to_process(code_string)
            
            output = self.wait_for_response()

            self._thread_lock.release()
        
            return output

    def pipe_to_process(self, string):
        if self.is_alive:
            self.process.stdin.write(self.format_code(string))
            self.process.stdin.flush()
        return

    def read_stdout(self, text=""):
        """ Continually reads the stdout from the self.process """
        while self.is_alive:
            if self.process.poll():
                self.is_alive = False
                break
            try:
                # Check contents of file
                self._thread_lock.acquire()
                self.get_response()
                self._thread_lock.release()
                time.sleep(0.05)
            except ValueError as e:
                print(e)
                return
        return

    def print_to_console(self, string):
        lines = [line.replace("\n", "") for line in string.split("\n") if len(line.strip()) > 0]
        for i, line in enumerate(lines):
            if i == 0:
                start = self.prompt
            else:
                start = "." * len(self.prompt)
            sys.stdout.write("{} {}".format(start, line))
            sys.stdout.flush()
        return

    def wait_for_response(self):
        time.sleep(0.05)
        return self.get_response()

    def get_response(self):
        """ Waits a small amount of time to see if a process produces text output """        
        self.stdout.seek(0)

        lines = []
        
        for stdout_line in iter(self.stdout.readline, ""):

            output = stdout_line.rstrip()

            # If printing to console, write the original line

            if self.silent:

                sys.stdout.write(stdout_line)

            else:

                sys.stdout.write(output)
            
            lines.append(output)
        
        # clear tmpfile
        self.stdout.truncate(0)
        
        return "\n".join(lines)

    def kill(self):
        """ Called to properly exit the subprocess and threads """
        self.is_alive = False
        if self.process.poll() is None:
            try:
                self.process.communicate(timeout=3)
            except TimeoutExpired:
                self.process.kill()
                self.process.communicate()
        if self.stdout_thread is not None:
            self.stdout_thread.join(1)
        return

    def contains_error(self, response):
        """ Returns True if the response from the Interpreter signals an error """
        return

    def get_nudge_code(self, value):
        """ Code for adjusting clock nudge by `value` seconds """
        return
    def get_random_seed_setter(self, seed):
        """ Returns code for setting the same random seed value """
        return

    def get_stop_sound(self):
        """ Returns the code for stopping all sound / clearing a scheduling clock """
        return

    def get_solo_code(self, string, on):
        """ Returns code for solo-ing a single codelet / workspace text. Should 
            return None if no streams exist. `on` is a bool for solo-ing or desolo-ing"""
        return None

    def get_reset_code(self, local_code, codelet_code):
        """ Returns code necessary to reset program state. If codelet_code is empty,
            stop any streams. If it exists, reset streams and apply codelet_code """
        return

    def add_to_colour_map(self, regex, colour, name=None):
        ident = str(name) if name is not None else "colour_map_{}".format(len(self._colour_map))
        self._colour_map[ident] = (regex, colour)
        return

    def get_formatting(self):
        """ Returns a dict of """
        return self._colour_map

    def findstyles(self, line, *args):
        """ Finds any locations of any regex and returns the name
            of the style and the start and end point in the line """

        tags = self._colour_map.keys()

        pos = []

        for tag in tags:

            match_start = match_end = 0

            for match in re.finditer(self._colour_map[tag][0], line):

                looking = True

                i = 0

                while looking:

                    try:

                        start  = match.start(i)
                        end    = match.end(i)

                        if start == end == -1:

                            raise IndexError # this is hacky af

                        match_start = start
                        match_end   = end

                    except IndexError:

                        looking = False

                    i += 1

                pos.append((tag, match_start, match_end))

        return pos

    def add_banned_command(self, regex):
        """ Add a RegEx that will flag a code execution as disallowed when found """
        self._banned_commands.append(re.compile(regex))

    def add_unmonitored_command(self, regex):
        """ Add a RegEx that will flag a code execution as disallowed when found """
        self._unmonitored_commands.append(re.compile(regex))

    def get_banned_commands(self):
        return self._banned_commands

    def get_unmonitored_commands(self):
        return self._unmonitored_commands

class FoxDot(Interpreter):
    path = "{} -u -m FoxDot --pipe".format(PYTHON_EXECUTABLE)
    re_streams = r"(\w+)\s*>>"
    name_short = "foxdot"
    name_long  = "FoxDot"
    ident = 0
    def __init__(self, *args, **kwargs):
        Interpreter.__init__(self, self.__class__.path, *args, **kwargs)

        # Ban local changes to tempo / clock stopping
        self.add_banned_command(r".*(Clock\s*\.\s*bpm\s*[\+\-\*\/]*\s*=\s*.+)")
        self.add_banned_command(r".*(Clock\s*\.\s*clear\(\s*\))")

        self.add_unmonitored_command(r".*(\.solo\(.*\))")

        # Set up syntax colouring

        self.add_to_colour_map(r"(?<=def )(\w+)", '#29abe2', name="user_defn")
        self.add_to_colour_map(r"(?<=>>)(\s*\w+)", '#ec4e20', name="players")
        self.add_to_colour_map(r"^\s*#.*|[^\"']*(#[^\"']*$)", '#666666', name="comments")
        self.add_to_colour_map(r"\W+(\d+)", '#e89c18', name="numbers")
        self.add_to_colour_map(r"\".*?\"|\".*" + "|\'.*?\'|\'.*", "Green", name="strings")
        self.add_to_colour_map(r"\s>>\s?", "#e89c18", name="arrow", )

    def kill(self):
        self.execute("Clock.stop()")
        return Interpreter.kill(self)

    def format_code(self, string):
        return "{}\n\n".format(string)

    def start_server(self):
        return self.execute("allow_connections()", verbose=False)

    def stop_server(self):
        return self.execute("allow_connections(False)", verbose=False)

    def sync_to_server(self, ip_address):
        return self.execute("Clock.connect('{}')".format(ip_address), verbose=False)

    def contains_error(self, response):
        return response.startswith("Traceback") if type(response) == str else False

    def get_nudge_code(self, value):
        return "Clock.nudge = {}".format(value)

    def get_streams(self, string):
        """ Uses RegEx to return the FoxDot players in a block of text """
        return re.findall(r"(\w+)\s*>>", string)

    def get_random_seed_setter(self, seed):
        """ Returns code for setting the same random seed value """
        return "RandomGenerator.set_override_seed({})".format(seed)

    def get_stop_sound(self):
        """ Returns the code for stopping all sound / clearing a scheduling clock """
        return "Clock.clear()"

    def get_solo_code(self, string, on):
        players = self.get_streams(string)
        if len(players) > 1:
            cmd = "Group({}).solo({})".format(", ".join(players), int(on))
        elif len(players) == 1:
            cmd = "{}.solo({})".format(players[0], int(on))
        else:
            cmd = None
        return cmd

    def get_reset_code(self, local_code, codelet_code):
        reset_code = []
        
        # Stop players if there isn't a codelet to reset to
        if codelet_code == "":
            func = "stop"
        else:
            func = "reset"

        # Add reset/stop code
        players = self.get_streams(local_code)
        for player in players:
            reset_code.append("{}.{}()".format(player, func))

        # Re-apply codelet text if it exists
        if codelet_code != "":
            reset_code.append(codelet_code)

        return "\n".join(reset_code)

class TidalCycles(Interpreter):
    path = 'ghci'
    prompt = "tidal>"
    re_streams = r"(d\d)\s*"
    name_short = "tidalcycles"
    name_long  = "TidalCycles"
    ident = 1
    def __init__(self, *args, **kwargs):
        Interpreter.__init__(self, self.__class__.path, *args, **kwargs)

        # Ban local changes to tempo / clock stopping
        self.add_banned_command(r".*cps.*")
        self.add_banned_command(r".*hush.*")

        # Set up syntax colouring
        self.add_to_colour_map(r"(?<=>>)(\s*\w+)", '#ec4e20', name="players")
        self.add_to_colour_map(r"^\s*--.*|[^\"']*(--[^\"']*$)", '#666666', name="comments")
        self.add_to_colour_map(r"\W+(\d+)", '#e89c18', name="numbers")
        self.add_to_colour_map(r"\$|#", "Dark Green", name="syntax", )
        self.add_to_colour_map(r"\".*?\"|\".*" + "|\'.*?\'|\'.*", "Green", name="strings")

    def execute_setup_code(self):
        # Import and setup tidal

        from .boot.tidal import bootstrap

        for line in bootstrap.split("\n"):

            self.process.stdin.write(line.rstrip() + "\n")
            self.process.stdin.flush()

        return

    def get_stop_sound(self):
        """ Returns the code for stopping all sound / clearing a scheduling clock """
        return "hush"

    def get_nudge_code(self, value):
        return "nudge {}".format(value)

    def get_solo_code(self, string, on):
        # need to add
        return None

    def get_reset_code(self, local_code, codelet_code):
        reset_code = []
        
        # Add reset/stop code
        streams = self.get_streams(local_code)

        for stream in streams:
           
            reset_code.append("{} $ silence".format(stream))

        # Re-apply codelet text if it exists

        if codelet_code != "":
        
            reset_code.append(codelet_code)

        return "do {\n" + ";\n".join(reset_code) + "\n}\n"

    def format_code(self, string):
        """ Used to formant multiple lines in haskell """
        return ":{\n" + string + "\n:}\n"

    def contains_error(self, response):
        return response.lstrip().startswith("<interactive>") if type(response) == str else False

class TidalCyclesStack(TidalCycles):
    path = "stack ghci"
    name_short = "tidalcyclesstack"
    name_long  = "TidalCycles (Stack)"



LANGUAGE_IDENT = {  FoxDot.get_short_name() : FoxDot,
                    TidalCycles.get_short_name() : TidalCycles,
                    TidalCyclesStack.get_short_name() : TidalCyclesStack }

LANGUAGE_NAMES = { FoxDot.get_name() : FoxDot.get_short_name(),
                   TidalCycles.get_name() : TidalCycles.get_short_name(),
                   TidalCyclesStack.get_name() : TidalCyclesStack.get_short_name() }

def get_interpreter(name):
    return LANGUAGE_IDENT.get(name.lower(), None)

def get_short_name(long_name):
    return LANGUAGE_NAMES[long_name]