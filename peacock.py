from io import StringIO
from itertools import zip_longest
import sys
from threading import Thread

from peacock.interact import MacKeyboard, InteractANSIMac, _BufferInteract 


class Peacock(Thread):
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

    dir_to_cart = {'up': (-1,0), 'down': (1, 0), 
                   'left': (0, -1), 'right': (0, 1)}
    
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
        
        # Users can register key handlers to give app specific key-bindings
        # Certain keys (delete, arrow keys) have default behaviors that 
        # users would expect, but they can easily be overriden with the
        # 'on' decorator
        # handlers: str -> ((str, int) -> None)
        self.handlers = {}
        self.register_default_handlers()
        
        ############################## CURSOR METHODS #########################
        # To ease use, a number of utility methods are wrapped here to 
        # interface with the interact library
        self.move_cursor = self.interact.move_cursor
        self.move_cursor_to = self.interact.move_cursor_to
        self.move_cursor_to_x = self.interact.move_cursor_to_x
        self.move_cursor_to_eol = self.interact.move_cursor_to_eol
        self.move_cursor_to_beginning = self.interact.move_cursor_to_beginning
        self.save_cursor = self.interact.move_cursor

        # Let's GOOOO
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

    def run(self):
        """
            Main event loop of the app. On each loop, checks to see if it is
            still running, and then if there is a key queued, triggers the key
            handler for that key
        """
        while self.running:
            key = self.keyboard.get_key_or_none()
            if key:
                self.handle(key)
    
    def stop(self):
        """
            Stops the application from running on the next iteration of the 
            event loop, and kills the keyboard handler
        """
        self.running = False
        self.keyboard.stop()

    ############################################################################
    ########################### EVENT HANDLER METHODS ##########################
    ############################################################################
    def on(self, key):
        """
            Add "on-key" handlers to this app. Called with a key, (soon to
            support multi-key sequences), and returns a decorator that 
            consumes a function, and binds the original key sequence to be
            handled by the given function. The function will be called with: 
                * str - the text of the line that the cursor is in
                * int - the current x position of the cursor in that line 
            E.g.:
            >>> app = Peacock()
            >>> @app.on("ctrl+x")
            ... def delete_to_beginning(cur_line, x):
            ...     # Deletes the text before the cursor, 
            ...     # and returns the chars deleted
            ...     app.delete(x)
        """
        # TODO: add multi-key sequences

        # Validate that it is in fact a valid key sequence
        if key not in self.keyboard.keys.values():
            raise ValueError("{} not a valid key".format(key))

        def inst_decorator(f):
            """
                Decorator closure that binds the key-sequence specified in
                the outer scope to the given function
                :param f: (str, int) -> None - void function which consumes the 
                    current line text and cursor x-position 
                :return: f - unaltered
            """
            self.handlers[key] = f 
            return f 
        return inst_decorator

    def handle(self, key):
        """
            Executes whatever action is associated with the given key
            :param key: str - a key code or sequence (non-None)
        """
        # TODO: add multi-key sequences

        # If there is a custom behavior associated with the given key,
        # execute that
        if self.handlers.get(key, None):
            # Handlers is a dict of mapping str -> ((str, int) -> None)
            # Call the function with the current line's text, and the 
            # x position in that line
            return self.handlers[key](self._buffer[self._y], self._x)
        else:
            # if there is no custom handler associated with the given key
            # and echo mode is on, write the key at the current cursor 
            # position
            if self.echo:
                self.write(key)

    def register_default_handlers(self):
        """
            Binds default behavior to the certain "special" keys. Specifically,
            binds the arrow keys to move the cursor in the implied direciton,
            the delete key to remove a character behind the cursor, and enter
            to insert a newline a the cursor
        """

        def arrow_handler_factory(rows, cols):
            """
                Returns a function that moves the cursor the given coordinates  
                :param rows: int - number of rows to move for the given direc
                :param cols: int - number of cols to move for the given direc
                :return: (str, int) -> None
            """
            def arrow_handler(*args):
                self.interact.move_cursor(rows, cols)
            return arrow_handler
        
        # For each of the directions and associated movement coordinates,
        # use self.on(direc) to create a decorator that binds behavior to
        # the given direc, and then use that decorator to bind
        # the function which moves the given number for rows and cols 
        for direc, (rows, cols) in self.dir_to_cart.items():
            self.on(direc)(arrow_handler_factory(rows, cols))

        @self.on("delete") 
        def delete_handler(*args):
            # On backspace, delete one character 
            self.interact.delete(1)

        @self.on("enter")
        def enter_handler(curr_line, x):
            # On enter, write a new line 
            self.write("\n")

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

    def reset(self):
        """
            Resets this application object and the terminal to the state
            it was when started
        """
        self.clear()
        self.interact.reset()
        self.handlers = {}
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
        return self.interact.x

    @_x.setter
    def _x(self, value):
        self.interact.x = value
    
    @property
    def _y(self):
        return self.interact.y

    @_y.setter
    def _y(self, value):
        self.interact.y = value

    @property
    def _buffer(self):
        return self.interact._buffer
