from io import StringIO
import sys
from threading import Thread, Event

from .mode import Mode, ModeError
from peacock.interact import MacKeyboard, InteractANSIMac

class Peacock:
    """
        The Peacock object is the public interface to this framework, and
        has a Flask-esque interface. Once created, takes over writing and 
        key handling from the specified TTY, so 'app.read' and 'app.write'
        should be used in their place
        E.g.
        >>> app = Peacock()
        >>> file_name = "my_file.txt"
        >>> @app.on("ctrl+x")
        ... def delete_to_beginning(cur_line, x):
        ...     # Deletes the text before the cursor, 
        ...     # and returns the chars deleted
        ...     app.delete(x)
        >>>
        >>> @app.on("ctrl+n")
        ... def open_new(*args):
        ...     app.save(file_name)
        ...     file_name = app.read(format("{|green}", "What file should I open?"))
        ...     app.clear()
        ...     app.write(open(file_name).read()) 

        See the examples directory for more full-featured examples
    """

    
    def __init__(self, echo=True, running=True, insert=True, line_length=120,
                 out=sys.stdout, debug=False):
        """
            Instantiates a Peacock app and begin's it running in the its own
            thread. Once created, it will perform various option changes to
            'out', so it is STRONGLY RECOMMENDED that you do not perform any
            explicit 'print' or 'write' operations to the file descriptor 
            that is passed in as 'out'. 

            :param echo: bool - Should keystrokes be echoed to 'out' as they
                are typed?
            :param running: bool - should this thread be started immediately?
            :param insert: bool - When the user is typing with text in front
                of the cursor, should the characters be inserted behind the
                trailing text, or should they overwrite?
            :param line-length: int - How long do we allow lines to be be?
            :param out: file-descriptor - should be a TTY or PTY fd that is
                connected to a terminal-emulator that supports ANSI control
                sequences
            :param debug: bool - debug mode
        """
        super().__init__()
        self.echo = echo
        self.running = running 
        self.insert = insert
        self.line_length = line_length
        self.out = out
        self.debug = debug
        
        # A keyboard interface for the current app. I believe the 'MacKeyboard'
        # interface will work for Unix systems as well, but it must be tested
        self.keyboard = MacKeyboard()
        self.interact = InteractANSIMac(self.keyboard, out, line_length)
        
        # Additionally, the app and users can create modes, in which keys have
        # different behaviors. These bindings can be added by adding the `mode`
        # keyword to on, and providing either a string name, or subclassing
        # `Mode` for more complex behavior, and providing an instance of the 
        # class
        # By default all apps have two modes, insert and read
        self.modes = {}
        self.mode = None
        self.configure_default_modes()

        
        # Users can register key handlers to give app specific key-bindings
        # Certain keys (delete, arrow keys) have default behaviors that 
        # users would expect, but they can easily be overriden with the
        # 'on' decorator
        self.register_default_handlers()
        

        ############################## CURSOR METHODS #########################
        # To ease use, a number of utility methods are wrapped here to 
        # interface with the interact library
        self.move_cursor = self.interact.move_cursor
        self.move_cursor_to = self.interact.move_cursor_to
        self.move_cursor_to_x = self.interact.move_cursor_to_x
        self.move_cursor_to_eol = self.interact.move_cursor_to_eol
        self.move_cursor_to_beginning = self.interact.move_cursor_to_beginning
        self.save_cursor = self.interact.save_cursor

        # Let's GOOOO
        self.running = Event()
        self.thread = Thread(target=self.event_loop, args=(self.running))
        self.start()

    def trailing_output(self):
        """
            Returns all text after the current cursor position. Useful for
            inserting text. E.g.:
            >>> app = Peacock()
            >>> app.write("Hello\nWorld!")
            >>> app.move_cursor(-1, -3)
            >>> app.trailing_output()
            "llo\nWorld!"

        """
        after_cursor = '\n'.join(self._buffer[self._y:])
        return after_cursor[self._x:]

    def event_loop(self, flag):
        """
            Main event loop of the app. On each loop, checks to see if it is
            still running, and then if there is a key queued, triggers the key
            handler for that key
        """
        while not flag.is_set():
            key = self.keyboard.get_key_or_none()
            if key:
                self.handle(key)

    def stop(self):
        """
            Stops the application from running on the next iteration of the 
            event loop, and kills the keyboard handler
        """
        self.running.set()
        self.keyboard.stop()

    ############################################################################
    ########################### EVENT HANDLER METHODS ##########################
    ############################################################################
    def on(self, key, mode="insert"):
        """
            Add "on-key" handlers to the given mode. Raises `ModeException` if 
            the specified mode has not been registered with the app. 
            Called with a key, (soon to support multi-key sequences), and 
            returns a decorator that consumes a function, and binds the original 
            key sequence to be handled by the given function in the given mode. 
            By default, the function will be called with: 
                * Peacock - a reference to the currently running app
                * str - the text of the line that the cursor is in
                * int - the current x position of the cursor in that line 
            However, by subclassing `Mode` and overriding the `handle` method, 
            the key-handler function signatures can be arbitrarily customized
            E.g.:
            >>> app = Peacock()
            >>> @app.on("ctrl+x")
            ... def delete_to_beginning(app, cur_line, x):
            ...     # Deletes the text before the cursor when in insert mode 
            ...     app.delete(x)
        """
        # TODO: add multi-key sequences
        try:
            return self.modes[mode].on(key)
        except KeyError:
            raise ModeError("{} has not been added yet. All modes must be "
                            "added via Peacock.add_mode() before they can be "
                            "used.".format(mode))
    
    def handle(self, key):
        """
            Executes whatever action is associated with the given key
            :param key: str - a key code or sequence (non-None)
        """
        # TODO: add multi-key sequences
        mode = self.mode
        while mode:
            # If there is a custom behavior associated with the given key
            # in the current mode, execute it
            if mode.handlers.get(key, None):
                # Handlers is a dict of mapping:
                #   str -> ((Peacock, str, int) -> None)
                # Call the function with the current app, the current line's 
                # text and the x position in that line
                return mode.handle(key, app=self)
            else:
                # Else, escalate to the parent mode, if any, and recurse 
                mode = mode.parent
    
    ############################################################################
    ############################  MODE METHODS   ###############################
    ############################################################################
   
    def add_mode(self, mode, name=None):
        """
            Adds the given mode to this app
            :param mode: Mode - The mode to add
            :param name: str - the name to associate the given mode to
        """
        self.modes[name or mode.name] = mode
   
    def set_mode(self, name):
        """
            Tries to activate the mode with the associated name
            :param name: str - the name of the mode to activate
        """
        try:
            self.mode = self.modes[name]
        except KeyError:
            raise ModeError("Set Mode: {} is not a registered mode. Please add "
                            "it first with Peacock.add_mode".format(name))

    def configure_default_modes(self):
        """
            Sets up the default modes for a Peacock applications, specifically
            "Insert" mode, which allows the user to insert text, and "Read"
            mode, which allows an app to read text from a user
            Finally, activates "Insert"
        """
        for mode in ("insert", "read"):
            self.modes[mode] = Mode(mode, self.keyboard)
        self.mode = self.modes["insert"] 

    ############################################################################
    #############################   IO METHODS   ###############################
    ############################################################################
   
    def write(self, msg):
        """
            Writes msg to 'out' at the current cursor position. This is the
            interface that should be used for all output to 'out' in lieu
            of 'print', as it updates the internal representation 
        """
        # TODO add optimization for write_char
        self.interact.write(msg)

    def delete(self, chars):
        """
            Delete's 'chars' characters from behind the current cursor position
            and moves all text back
            :param chars: int - number of characters to delete
        """
        # TODO add optimization for delete_char
        self.interact.delete(chars)

    def read(self, prompt):
        self.mode = read = self.modes["read"]
        reader = Thread(target=self.event_loop, args=(read.is_reading,))
        reader.start()
        reader.join()
        return read

    def reset(self):
        """
            Resets this application object and the terminal to the state
            it was when started
        """
        self.clear()
        self.interact.reset()
        self.modes = {}
        self.configure_default_modes()
        self.register_default_handlers()

    def clear(self):
        """
            Deletes all of the text that this app wrote to the terminal and
            returns the cursor to the origin
        """
        #TODO: Implement this method
        pass


    ############################################################################
    #############################  PRIVATE FIELDS  #############################
    ############################################################################
    @property
    def _x(self):
        # The current cursor X position, should only be used internally as a 
        # convenience
        return self.interact.x

    @_x.setter
    def _x(self, value):
        # Set the current cursor X position, should only be used internally as
        # a convenience, please favor move_cursor()
        self.interact.x = value
    
    @property
    def _y(self):
        # The current cursor Y position, should only be used internally as a 
        # convenience
        return self.interact.y

    @_y.setter
    def _y(self, value):
        # Set the current cursor Y position, should only be used internally as
        # convenience, please favor move_cursor()
        self.interact.y = value

    @property
    def _buffer(self):
        # Allows you to access interacts file buffer
        return self.interact._buffer
