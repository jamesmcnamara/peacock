from io import StringIO
from itertools import count

class Interact:
    """
        Abstract base class for the interactions. Supports a few common
        utility functions
    """
 
    def __init__(self, keyboard, out, line_length):
        """
            :param keyboard: a subclass of peacock.keyboard.Keyboard 
            :param out: file-descriptor - should be a TTY or PTY fd that is
                connected to a terminal-emulator that supports ANSI control
                sequences
            :param line-length: int - line length supported in 'out'
        """
        self.keyboard = keyboard
        self.out = out
        self.line_length = line_length
        self.x, self.y = 0, 0
    
        # Private Variables
        # Because the 'out' fd is a TTY, we can't read from it. In order to 
        # correctly append trailing text, and keep the user in a sandboxed 
        # environment (i.e. unable to edit terminal output unrelated to the
        # current activity), we must maintain an internal representation of
        # all the text created and deleted, as well as cursor position 
        self._buffer = [""]

    def reset(self):
        """
            Resets this application object and the terminal to the state
            it was when started
        """
        self.move_cursor_to(0, 0)
        self.out.truncate(0)
        self.out.seek(0)
        self._buffer = [""]
    
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
        y = min(max(0, self.y + rows), len(self._buffer) - 1)
         
        # length of the current line, assuming the translation to new 
        # y has already happened
        curr_line_length = len(self._buffer[y])
        
        #New x value after translation. Clipped within the range of 
        # 0 - line length
        x = min(max(0, self.x + cols), curr_line_length)
        
        # Moves the cursor the delta between _x, _y and x, y
        self._move_cursor(y - self.y, x - self.x)

    def move_cursor_to(self, x=-1, y=-1):
        """
            Moves the cursor to the "absolute" x, y  position 
            However, values are still clipped between 0 and max 
        """
        delta_x = delta_y = 0
        if y > -1:
            # If y is non-negative, Set _y to y, clipped between 0 and 
            # buffer length 
            delta_y = min(y, len(self._buffer) - 1) - self.y
        if x > -1:
            # If x is non-negative, Set _x to x, clipped between 0 and 
            # current line length
            curr_line_len = len(self._buffer[self.y + delta_y])
            delta_x = min(x, curr_line_len) - self.x
        
        # Move the terminal cursor to _x
        self.move_cursor(delta_y, delta_x)
    
    def move_cursor_to_x(self, x=0, line_length=None):
        """
            Moves the cursor to the "absolute" x position in the current line
            However, values are still clipped between 0 and line length 
        """
        line_length = line_length or self.line_length
         
        # move it to the beginning of the line, then move it forward x
        self.move_cursor(cols=-line_length)
        self.move_cursor(cols=x)
    
    def move_cursor_to_eol(self, rows=0, line_length=None):
        """
            Moves the cursor to the eol of the line that is 'rows' displaced
            from the current position. Still capped between 0 length buffer.
            So app.move_cursor_to_eol(-3) moves it to eol of the 3 lines 
            before the current position
        """
        self.move_cursor(rows=rows)
        self.move_cursor_to_x(self.line_length)

    def move_cursor_to_beginning(self, rows=0, line_length=None):
        """
            Moves the cursor to the beginning of the line that is 'rows' 
            displaced from the current position. Still capped between 0 length 
            of buffer. So app.move_cursor_to_beginning(-3) moves it to beginning
            of the 3 lines before the current position
        """
        self.move_cursor(rows=rows)
        self.move_cursor_to_x(-self.line_length) 

    def save_cursor(self):
        """
            Save the current location of the cursor, and returns a closure
            that when called, will shift the cursor back to the position 
            it was in when called. Kinda neat, huh?
        """
        x, y = self.x, self.y
        def restore():
            # Closes over the old values of (x, y), then when called, 
            # calculates the delta, and shifts
            delta_y = y - self.y
            delta_x = x - self.x
            self.move_cursor(delta_y, delta_x)
        return restore
    
    def _move_cursor(self, rows=0, cols=0):
        """
            All classes must implement a method that displaces the cursor by 
            'rows' rows then 'cols' cols
        """
        raise NotImplementedError("All subclasses of Interact must "
                                  "implement move_cursor")

    
    ############################################################################
    ##############################  IO METHODS  ################################
    ############################################################################
    def write(self, msg):
        
        trailing_output = self.trailing_output()
        output = msg + trailing_output
        first_line, *rest_lines = output.split("\n")
        self._buffer[self.y] = self.text_before_cursor() + first_line
        self._buffer[self.y + 1:] = rest_lines
        
        *lines, last = output.split("\n")
        for line in lines:
            self._delete_line_out()
            self.out.write(line + "\n")
            self.y += 1
            self.x = 0
        self._delete_line_out()
        self.out.write(last)
        self.x += len(last)

        first, *rest = trailing_output.split("\n")
        self.move_cursor_to_eol(-len(rest))
        self.move_cursor(cols=-len(first))

    def delete(self, chars):
        text_after_cursor = self.text_after_cursor()
        x, y = self._calculate_ending_position(chars)
        trailing_output = self.trailing_output()
        self.move_cursor_to(x, y)
        restore = self.save_cursor()
        self.delete_trailing()
        self.write(trailing_output)
        restore()

    def delete_trailing(self):
        restore = self.save_cursor()
        for _ in self._buffer[self.y:]:
            self.delete_line()
            self.move_cursor_to_beginning(1)
        restore()
        del self._buffer[self.y + 1:]  
    
    def delete_line(self):
        self._buffer[self.y] = self.text_before_cursor()
        self._delete_line_out()

    ############################################################################
    ############################ UTILITY FUNCTIONS #############################
    ############################################################################
    def trailing_output(self):
        """
            Returns all text after the current cursor position. Useful for
            inserting text. E.g.:
            >>> interact = InteractANSIMac()
            >>> interact.write("Hello\nWorld!")
            >>> interact.move_cursor(-1, -3)
            >>> interact.trailing_output()
            "llo\nWorld!"

        """
        after_cursor = '\n'.join(self._buffer[self.y:])
        return after_cursor[self.x:]

    def text_after_cursor(self):
        """
            Returns the text after the cursor in the current line 
        """
        return self._buffer[self.y][self.x:]
    
    def text_before_cursor(self):
        """
            Returns the text before the cursor in the current line 
        """
        return self._buffer[self.y][:self.x]

    def _calculate_ending_position(self, chars):
        x, y = self.x, self.y
        while chars > x and y > 0:
            chars -= x + 1
            y -= 1
            x = len(self._buffer[y])
        return max(0, x - chars), max(0, y)

class InteractANSIMac(Interact):
    """
        Low-level interface for managing interaction with the terminal, 
        using ANSI escape sequences. Assumes that the terminal has been 
        placed into cbreak (rare) or raw mode.

        More info on ANSI escape sequences:
            http://en.wikipedia.org/wiki/ANSI_escape_code
    """
    def __init__(self, keyboard, out, line_length):
        super().__init__(keyboard, out, line_length)
        
        # Default ANSI escape sequence is Esc+[
        self.escape_seq = "\033["

    
    
    def _move_cursor(self, rows=0, cols=0):
        """
            Moves the cursor the given number of rows, THEN the given number
            of rows. This does NOT move the cursor to the given coordinate
            (rows, cols), but instead moves relatively
            Any values that are too large are clipped to the max possible
            given the constraints (i.e. length of line, length of buffer)
            :param rows: int - number of rows to move, negatives allowed 
            :param cols: int - number of cols to move, negatives allowed 
        """

        if rows:
            self.out.write("{}{}{}".format(self.escape_seq, abs(rows), 
                                           'B' if rows > 0 else 'A'))
            self.y += rows
        if cols:
            self.out.write("{}{}{}".format(self.escape_seq, abs(cols), 
                                           'C' if cols > 0 else 'D'))
            self.x += cols
        self.out.flush()

    def delete_display(self):
        """
            Clears the ENTIRE visible terminal view, not just the app
            space, so really, this probably shouldn't even be here
        """
        self.out.write("{}2J".format(self.escape_seq))
        self.out.flush()
    
    def delete_line(self):
        """
            Deletes the text after the cursor to the end of the line 
        """
        super().delete_line()
        self._delete_line_out()
        
    def _delete_line_out(self):
        self.out.write("{}K".format(self.escape_seq))
        self.out.flush()

class _BufferInteract(Interact):
    """
        Mock class for testing. Emulates a TTY that supports ANSI escape
        sequences. NOTE: This implementation is sloppy as fuck. It's private
        for that reason. Don't use it unless you know what you're doing
    """

    def __init__(self, keyboard, out, line_length):
        super().__init__(keyboard, out, line_length)
        
    def _move_cursor(self, rows=0, cols=0):
        """
            Moves the cursor the given number of rows, THEN the given number
            of cols. This does NOT move the cursor to the given coordinate
            (rows, cols), but instead moves relatively
            Any values that are too large are clipped to the max possible
            given the constraints (i.e. length of line, length of buffer)
            :param rows: int - number of rows to move, negatives allowed 
            :param cols: int - number of cols to move, negatives allowed 
        """

        self.y += rows
        self.x += cols

    def delete_display(self):
        """
            Wipes the output
        """
        self.out.truncate(0) 

    def delete_line(self):
        """
            Deletes the text after the cursor to the end of the line 
        """
        super().delete_line()
        self._delete_line_out()

    def _delete_line_out(self):
        self.out.truncate(0)
        self.out.seek(0)
        self.out.write("\n".join(line if i != self.y else line[:self.x] 
                                 for i, line in enumerate(self._buffer)))
        self.out.seek(self.off)
    
    def write(self, msg):
        self.out.seek(self.off)
        super().write(msg)

    @property
    def off(self):
        # The current offset is given by x + number of characters in each line
        # after the curret line plus 1 to account for the new line
        return self.x + sum(len(line) + 1 for line in self._buffer[:self.y])

