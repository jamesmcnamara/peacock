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

        # Private Variables
        # Because the 'out' fd is a TTY, we can't read from it. In order to 
        # correctly append trailing text, and keep the user in a sandboxed 
        # environment (i.e. unable to edit terminal output unrelated to the
        # current activity), we must maintain an internal representation of
        # all the text created and deleted, as well as cursor position 
        self._buffer = [""]
        self._x, self._y = 0, 0
        self.start()

    @property
    def trailing_output(self):
        """
            Returns all text after the current cursor position. Useful for
            inserting text. E.g.:
            >>> app = Peacock()
            >>> app.write("Hello\nWorld!")
            >>> app.move_cursor(-1, -3)
            >>> app.trailing_output
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
                try:
                    self.handle(key)
                except AssertionError:
                    self.stop()
                    d = locals()
                    d.update(globals())
                    from code import interact
                    interact(local=locals())
    
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
                self.move_cursor(rows, cols)
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
            self.delete(1)

        @self.on("enter")
        def enter_handler(curr_line, x):
            # On enter, write a new line 
            self.write("\n")
    
    ############################################################################
    ############################### CURSOR METHODS #############################
    ############################################################################
    def move_cursor(self, rows=0, cols=0):
        """
            Moves the cursor the given number of rows, THEN the given number
            of columns. This does NOT move the cursor to the given coordinate
            (rows, cols), but instead moves relatively
            Any values that are too large are clipped to the max possible
            given the constraints (i.e. length of line, length of buffer)
            :param rows: int - number of rows to move, negatives allowed 
            :param cols: int - number of cols to move, negatives allowed 
        """

        # New y value after translation. Clipped within the range of 
        # 0 - last-line
        y = min(max(0, self._y + rows), len(self._buffer) - 1)
         
        # length of the current line, assuming the translation to new 
        # y has already happened
        curr_line_length = len(self._buffer[y])
        
        #New x value after translation. Clipped within the range of 
        # 0 - line length
        x = min(max(0, self._x + cols), curr_line_length)
        
        # Moves the cursor the delta between _x, _y and x, y
        self.interact.move_cursor(y - self._y, x - self._x)

        # Set the internal cursor position to x and y
        self._x, self._y = x, y
    
    def move_cursor_to(self, x=-1, y=-1):
        """
            Moves the cursor to the "absolute" x, y  position 
            However, values are still clipped between 0 and max 
        """
        if y > -1:
            # If y is non-negative, Set _y to y, clipped between 0 and 
            # buffer length 
            self._y = min(y, len(self._buffer) - 1)
        if x > -1:
            # If x is non-negative, Set _x to x, clipped between 0 and 
            # current line length
            curr_line_len = len(self._buffer[self._y])
            self._x = min(x, curr_line_len)
        
        # Move the terminal cursor to _x
        self.interact.move_cursor_absolute(self._x, self._y)
    
    def move_cursor_to_x(self, x=0):
        """
            Moves the cursor to the "absolute" x position in the current line
            However, values are still clipped between 0 and line length 
        """
        # Set _x to x, clipped between 0 and current line length
        curr_line_len = len(self._buffer[self._y])
        self._x = max(0, min(x, curr_line_len))

        # Move the terminal cursor to _x
        self.interact.move_cursor_to_x(self._x)

    def move_cursor_to_eol(self, rows=0, line_length=None):
        """
            Moves the cursor to the eol of the line that is 'rows' displaced
            from the current position. Still capped between 0 length buffer.
            So app.move_cursor_to_eol(-3) moves it to eol of the 3 lines 
            before the current position
        """
        line_length = line_length or self.line_length
        self.move_cursor(rows=rows)
        self.move_cursor_to_x(line_length)

    def move_cursor_to_beginning(self, rows=0, line_length=None):
        """
            Moves the cursor to the beginning of the line that is 'rows' 
            displaced from the current position. Still capped between 0 length 
            of buffer. So app.move_cursor_to_beginning(-3) moves it to beginning
            of the 3 lines before the current position
        """
        line_length = line_length or self.line_length
        self.move_cursor(rows=rows)
        self.move_cursor_to_x(-line_length) 
    
    def save_cursor(self):
        x, y = self._x, self._y
        def restore():
            self.move_cursor(rows=y - self._y, cols=x - self._x)
        return restore
 
    def cursors_synced(self):
        return self._x == self.interact.x and self._y == self.interact.y

    ############################################################################
    ##############################  IO METHODS  ################################
    ############################################################################
   
    def write(self, msg):
        assert self.cursors_synced()
        trailing_output = self.trailing_output
        output = msg + trailing_output
        self.interact.write(output)
        first_line, *rest_lines = output.split("\n")
        self._buffer[self._y] = self._text_before_cursor() + first_line
        self._buffer[self._y + 1:] = rest_lines
        self._cursor_correction_terminal(trailing_output)
        self._cursor_correction_internal(msg)
        assert self.cursors_synced()

    def delete(self, chars):
        assert self.cursors_synced()
        text_after_cursor = self._text_after_cursor()
        x, y = self._calculate_ending_position(chars)
        if y != self._y: 
            trailing_lines = self._buffer[self._y + 1:]
            num_trailing_lines = len(self._buffer) - y 
            num_deleted_lines = self._y - y
            trailing_output = self.trailing_output
            self.move_cursor_to(x, y)
            restore = self.save_cursor()
            self.delete_trailing()
            self.write(trailing_output)
            restore()
        else:
            self.move_cursor_to_x(x)
            self.clear_line(x)
            restore = self.save_cursor()
            self.write(text_after_cursor)
            restore()
        assert self.cursors_synced()  

    def delete_trailing(self):
        assert self.cursors_synced()  
        restore = self.save_cursor()
        for _ in self._buffer[self._y:]:
            self.clear_line(self._x)
            self.move_cursor_to_beginning(1)
        restore()
        del self._buffer[self._y + 1:]  
        assert self.cursors_synced()  

    def clear_line(self, from_x=0):
        assert self.cursors_synced()  
        self.move_cursor_to_x(from_x)
        self.interact.delete_line()
        self._buffer[self._y] = self._text_before_cursor()
        assert self.cursors_synced()  

    def reset(self):
        """
            Resets this application object and the terminal to the state
            it was when started
        """
        self.clear()
        self._buffer = [""]
        # self.interact.move_cursor(-self._y, -self._x)
        self._x, self._y = 0, 0
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
    ############################## PRIVATE METHODS #############################
    ############################################################################
    def _text_after_cursor(self):
        """
            Returns the text after the cursor in the current line 
        """
        return self._buffer[self._y][self._x:]
    
    def _text_before_cursor(self):
        """
            Returns the text before the cursor in the current line 
        """
        return self._buffer[self._y][:self._x]


    def _cursor_correction_terminal(self, msg):
        first, *rest = msg.split("\n")
        self.interact.move_cursor(rows=-len(rest), cols=-len(first))

    def _cursor_correction_internal(self, msg):
        *lines, last = msg.split("\n")
        x, y = len(last), len(lines) 
        if y:
            self._x = x
            self._y += y
        else:
            self._x += x
    
    def _write_out(self, msg):
        """
            Writes the given message out, without updating the internal
            representation
            :param msg: str - message to write out
        """
        if not self.insert:
            # If in overwrite mode, just write the message at the current
            # cursor location
            self.interact.write(msg)
        else:
            # Otherwise, we must write the message, and then rewrite the
            # trailing output, and restore the cursor position
            self.interact.write(msg)
            restore = self.save_cursor()
            self.interact.write(self.trailing_output)
            restore()

    def _write_buffer(self, msg):
        """
            Updates the internal representaiton with the given message added
            at current cursor position
            :param msg: str - message to write out
        """
        curr_line, text_after_cursor = self._curr_line_and_trail_text()
        if '\n' == msg:
            # If the message is a new line, trim the current line at the cursor
            # move the cursor to the start of the next line, and add a new line 
            # to the buffer which holds the text after the cursor 
            curr_line.truncate(self._x)
            self._y += 1
            self._x = 0
            self._buffer.insert(self._y, StringIO(text_after_cursor))
        elif '\n' in msg:
            # If it's a multiline message, we have some more work to do
            # First we need the first and last lines, and any additional lines
            # in the middle
            # E.g. we have _buffer = buf = ["hello", "world"], cursor pos is 
            # _x = 2, _y = 0 (after the "e" in "hello"), we are writing
            # "elephant\ncage", so first_line = "elephant", last_line is "cage"
            # and rest_lines is [] 
            first_line, *rest_lines, last_line = map(StringIO, msg.split('\n'))
            
            # Write the first line text into the current line after the cursor
            # E.g. "hello" becomes "heelphant"
            curr_line.seek(self._x)
            curr_line.write(first_line.getvalue())
            
            # Append the text after the cursor on the current line to the end
            # of the last line, and add last_line to rest lines
            # E.g. last_line becomes "cagello", rest_lines becomes ["cagello"]
            last_line.read()
            last_line.write(text_after_cursor)
            rest_lines.append(last_line)

            # Insert rest lines into buffer on the next line
            # E.g. buf = ["heelephant", "cagello", "world"]
            self._buffer[self._y + 1: self._y + 1] = rest_lines

            # _x becomes the pos after the inserted text on the last line
            # E.g. _x = 7 - 3 = 4
            self._x = len(last_line.getvalue()) - len(text_after_cursor) 

            # _y increases by the number of lines we inserted
            # E.g. _y = 0 + 1 = 1
            self._y += len(rest_lines)

        else:
            # If there are no new lines, we simply insert the text at the 
            # cursor, and update the _x position
            curr_line.seek(self._x)
            curr_line.write(msg + text_after_cursor)
            self._x += len(msg)

    def _calculate_ending_position(self, chars):
        x, y = self._x, self._y
        while chars > x and self._y > 0:
            chars -= x + 1
            y -= 1
            x = len(self._buffer[y])
        return max(0, x - chars), max(0, y)


    # def _delete_out(self, chars):
    #     """
    #         Deletes 'chars' characters from the terminal on the current line
    #         Does not update the current representation
    #         Requires that 'chars' is less than or equal to _x
    #         :param chars: int - number of characters to delete 
    #     """
    #     _, text_after_cursor = self._curr_line_and_trail_text()
    #     # Move the cursor back 'chars' characters
    #     self.interact.move_cursor(cols=-chars)

    #     # Delete from current position onwards
    #     self.interact.delete_line()

    #     # Write the trailing text of this line, and blank spaces to overwrite
    #     #self.interact.write(text_after_cursor + ' ' * chars)

    #     # Move the terminal cursor back
    #     #self.interact.move_cursor_to_x(self._x - chars)
    #         

    # def _delete_buffer(self, chars):
    #     """
    #         Deletes 'chars' characters from the current line in the internal
    #         representation and updates cursor position
    #         Requires that 'chars' is less than or equal to _x
    #         NOTE: the internal representation does not maintain the add'l 
    #         spaces that the terminal has written in
    #         :param chars: int - number of characters to delete 
    #     """
    #     curr_line, text_after_cursor = self._curr_line_and_trail_text()
    #     curr_line_len = len(curr_line.getvalue())
    #     
    #     # Move to the new _x position, write the trailing text of the line in,
    #     # then delete everything at the end
    #     curr_line.truncate(self._x - chars)
    #     # curr_line.seek(self._x - chars)
    #     # curr_line.write(text_after_cursor)
    #     # curr_line.truncate(curr_line_len - chars)

    #     # Update _x
    #     self._x -= chars
