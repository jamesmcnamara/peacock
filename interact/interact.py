from abc import ABCMeta, abstractmethod
from io import StringIO
from itertools import count

class Interact:
    """
        Abstract base class for the interactions. Supports a few common
        utility functions
    """
    __metaclass__ = ABCMeta
 
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

    @abstractmethod
    def move_cursor(self, rows=0, cols=0):
        """
            All classes must implement a method that displaces the cursor by 
            'rows' rows then 'cols' cols
        """
        raise NotImplementedError("All subclasses of Interact must "
                                  "implement move_cursor")


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
        self.x, self.y = 0, 0

    def write(self, msg):
        *lines, last = msg.split("\n")
        for line in lines:
            self.delete_line()
            self.out.write(line + "\n")
            self.y += 1
            self.x = 0
        self.delete_line()
        self.out.write(last)
        self.x += len(last)
    
    
    def move_cursor(self, rows=0, cols=0):
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

    def move_cursor_absolute(self, x=0, y=0):
        """
            Moves the cursor to the absolute location specified by (x, y)
            :param x: int - x coordinate
            :param y: int - y coordinate
        """
        self.out.write("{}{};{}k".format(self.escape_seq, x, y))
        self.x, self.y = x, y
        self.out.flush()

    def delete_display(self):
        """
            Clears the ENTIRE visible terminal view, not just the app
            space, so really, this probably shouldn't even be here
        """
        self.out.write("{}2J".format(self.escape_seq))
        self.out.flush()
    
    def delete_line(self, flush=True):
        """
            Deletes the text after the cursor to the end of the line 
        """
        self.out.write("{}K".format(self.escape_seq))
        if flush:
            self.out.flush()

class _BufferInteract(Interact):
    """
        Mock class for testing. Emulates a TTY that supports ANSI escape
        sequences. NOTE: This implementation is sloppy as fuck. It's private
        for that reason. Don't use it unless you know what you're doing
    """

    def __init__(self, keyboard, out, line_length):
        super().__init__(keyboard, out, line_length)
        self.x, self.y = 0, 0
        
    def move_cursor(self, rows=0, cols=0):
        """
            Moves the cursor the given number of rows, THEN the given number
            of cols. This does NOT move the cursor to the given coordinate
            (rows, cols), but instead moves relatively
            Any values that are too large are clipped to the max possible
            given the constraints (i.e. length of line, length of buffer)
            :param rows: int - number of rows to move, negatives allowed 
            :param cols: int - number of cols to move, negatives allowed 
        """

        self.y = min(max(0, self.y + rows), len(self.array) - 1)
        self.x = min(max(0, self.x + cols), len(self.array[self.y]))

    def move_cursor_absolute(self, x=0, y=0):
        """
            Moves the cursor to the absolute location specified by (x, y)
            :param x: int - x coordinate
            :param y: int - y coordinate
        """
        self.x = x
        self.y = y

    def delete_display(self):
        """
            Wipes the output
        """
        self.out.truncate(0) 

    def delete_line(self):
        """
            Deletes the text after the cursor to the end of the line 
        """
        s = "\n".join(line if i != self.y else line[:self.x] 
                       for i, line in enumerate(self.array))
        
        # Write spaces until the new line
        self.out.seek(0)
        self.out.write(s)
        self.out.truncate(len(s))
    
    def write(self, msg):
        """
            Writes the given message out to the terminal buffer, plus moves
            all trailing text, and restores the cursor to be just after the 
            message
            :param msg: str - the message to write to the terminal
            :param trailing: str - the trailing text after the cursor to write
                to emulate inserts
        """

        self.out.truncate(self.off)
        *lines, last = msg.split("\n") 
        for line in lines:
            self.delete_line()
            self.out.write(line + "\n")
            self.y += 1
            self.x = 0
        self.delete_line()
        self.out.write(last)
        self.x += len(last)
    
    @property
    def array(self):
        # Buffer array of the lines in the output
        return self.out.getvalue().split('\n')

    @property
    def off(self):
        # The current offset is given by x + number of characters in each line
        # after the curret line plus 1 to account for the new line
        return self.x + sum(len(line) + 1 for line in self.array[:self.y])

    @property
    def trailing_output(self):
        """
            Returns all text after the current cursor position. Useful for
            inserting text. E.g.:
        """
        self.out.seek(self.off)
        return self.out.read()
