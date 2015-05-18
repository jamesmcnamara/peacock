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
    
        # Private Variables
        # Because the 'out' fd is a TTY, we can't read from it. In order to 
        # correctly append trailing text, and keep the user in a sandboxed 
        # environment (i.e. unable to edit terminal output unrelated to the
        # current activity), we must maintain an internal representation of
        # all the text created and deleted, as well as cursor position 
        self._buffer = [""]
        self.x, self.y = 0, 0

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
        self.move_cursor(rows=rows, cols=self.line_length)

    def move_cursor_to_beginning(self, rows=0, line_length=None):
        """
            Moves the cursor to the beginning of the line that is 'rows' 
            displaced from the current position. Still capped between 0 length 
            of buffer. So app.move_cursor_to_beginning(-3) moves it to beginning
            of the 3 lines before the current position
        """
        self.move_cursor(rows=rows, cols=-self.line_length)

    def move_cursor_to_eof(self):
        """
            Moves the cursor to the end of the file.
        """
        self.move_cursor(rows=len(self._buffer), cols=len(self._buffer[-1]))

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
        """
            Interface for writing messages to the `out` file descriptor. This 
            class (attempts to) maintain a sychronized buffer of what has been
            written out, so that it can simulate text insertion
            :param msg: str -- the message to write out
        """
        # The message that we're ACTUALLY going to write is the given message 
        # plus all the text that was after the cursor, which must be shifted
        trailing_output = self.trailing_output()
        output = msg + trailing_output
        
        ########################## WRITE TO BUFFER ############################
        # We will append the text before the cursor on this line to the text 
        # in the first line of the output, and that becomes the new current 
        # line in the buffer, and the rest of lines become the contents of the
        # rest of the buffer (remember, this contains all of the text that was
        # after the cursor in the first place)
        first_line, *rest_lines = output.split("\n")
        self._buffer[self.y] = self.text_before_cursor() + first_line
        self._buffer[self.y + 1:] = rest_lines
        
        
        ############################ WRITE TO OUT #############################
        # Next, we write the message to the `out` fd. Note that if any of the 
        # lines in the new buffer are shorter than the line that was previously 
        # there, the difference will remain on the line. Thus we must first 
        # delete the line, THEN write the new one
        *lines, last = output.split("\n")
        for line in lines:
            self._delete_line_out()
            self.out.write(line + "\n")
            self.y += 1
            self.x = 0

        # Delete the last line, and write out the new one. If there was no 
        # newline character in the text, this is the only code that would be
        # run, and it will still work
        self._delete_line_out()
        self.out.write(last)

        # x increases by the length of the last line
        self.x += len(last)

        ############################ CURSOR CORRECT ###########################
        # Since we meshed the message and trailing output together, we weren't
        # able to use our save/restore cursor trick. Instead, the cursor is 
        # currently at EOF. So we must first move it up the number of lines in 
        # in trailing output - 1, and from the end of the line, we move 
        # backwards the number of characters in the first line of the trailing
        # output. This will leave us at the last character of the inserted text
        first, *rest = trailing_output.split("\n")
        self.move_cursor_to_eol(-len(rest))
        self.move_cursor(cols=-len(first))

    def delete(self, chars):
        """
            Deletes `chars` characters from the `out` text, by moving the 
            cursor back `chars` characters (taking into account line lengths)
            and then writing what WAS the trailing text from that point, 
            effectively erasing the text in-between
            :param chars: int -- the number of chars to delete
        """
        # Absolute X, Y coordinates in the text where the cursor will be after
        # deleting `chars` characters
        x, y = self._calculate_ending_position(chars)
        
        # Current trailing text, which will be written at x, y
        trailing_output = self.trailing_output()
        self.move_cursor_to(x, y)

        # Save the location at x, y before we write
        restore = self.save_cursor()

        # Delete all text from x, y down, and then write the trailing text
        self.delete_trailing()
        self.write(trailing_output)
        
        # Restore the cursor position to x, y
        restore()

    def delete_trailing(self):
        """
            Deletes all trailing text from the cursor location to EOF
            Relies on delete_line 
        """
        # Save cursor location
        restore = self.save_cursor()
        for _ in self._buffer[self.y:]:
            # For each line in the buffer, delete the line, and move the next
            self.delete_line()
            self.move_cursor_to_beginning(1)

        # restore the cursor position
        restore()
        
        # Remove the trailing empties from the buffer. Once a user has deleted
        # line, they shouldn't be able to enter it without writing a newline
        del self._buffer[self.y + 1:]  
    
    def delete_line(self):
        """
            Deletes all the text in the current line after the cursor from 
            the buffer, then calls the private method _delete_line_out to 
            delete the line from `out`
            NOTE: this method is not implemented. Each subclass must implement
            it for the file type they are targetting
        """
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
        """
            Calculates the X, Y location in the text of the cursor if `chars`
            characters were deleted from the current cursor location. Takes 
            into account the length of each intermediary line
        """
        x, y = self.x, self.y
        while chars > x and y > 0:
            # So long as the number of characters to delete is longer than 
            # the current line, and we aren't at the first line of text yet
            # decrement chars by the number of characters in the current line
            chars -= x + 1
            y -= 1
            x = len(self._buffer[y])
        # Return the x, y coordinates calculated, but clamped at 0, 0
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
        """
            Deletes the text after the cursor to the end of the line 
        """
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
        """
            Deletes the text after the cursor to the end of the line 
        """
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
        # after the curret line plus 1 to account for the new line character
        return self.x + sum(len(line) + 1 for line in self._buffer[:self.y])

