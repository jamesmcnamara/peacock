from collections import deque
import sys
from threading import Thread
from tty import setcbreak
import termios 

class Keyboard(Thread):
    pass

class MacKeyboard(Keyboard):
    """
        Handler for retrieving keyboard keys as they are pressed by a user of a 
        macintosh computer. The primary interface for this class is get_key_or_none
        which is non-blocking, and thus may return None e.g.
        >>> keyboard = MacKeyboard()
        >>> key = keyboard.get_key_or_none()
        >>> while True:
        >>>     if key:
        >>>         handle_key(key)
        >>>     else:
        >>>         regular_action()            
    """
    
    def __init__(self):
        """
            Initiates this keyboard, starts the thread running and catching 
            user input
            NOTE: no other methods will be able to read from stdin, nor will 
            standard terminal behavior apply, as this class puts the terminal 
            into cbreak mode
        """
        super().__init__()
        self.daemon = True
        self.keys = mac_keys
        self.direc = mac_direc
        self._deque= deque()
        self.settings = termios.tcgetattr(sys.stdin)
        self.running = True
        self.start()
        
    def stop(self):
        """
            Stops this thread from collecting the output of from stdin,
            and returns stdin to whatever mode it was in when this thread
            started, (presumably cooked mode)
        """
        self.running = False
        termios.tcsetattr(sys.stdin, termios.TCSANOW, self.settings)
    

    def run(self):
        """
            Puts the keyboard into cbreak mode so it can read char by char
            from stdin, and places each char into a queue
        """
        setcbreak(sys.stdin)
        while self.running:
            ch = ord(sys.stdin.read(1))
            self._deque.append(self.keys[ch])

    def get_key_or_none(self):
        """
            primary interface for this class. Dequeues, and returns the last 
            pressed char if no key has been pressed since the last time this 
            was called and the queue is empty, returns None
            NOTE: Your applications event loop must call this frequently, as 
            this queue is FIFO, so each time the method is called, you will
            get the first key that was pressed since the last time the
            method was called
        """
        try:
            # see if there is an key in the queue
            ch = self._deque.popleft()
        except IndexError:
            # if no keys have been pressed, return None
            return None
        
        if ch != 'esc':
            # In the typical case where the key wasn't escape, just
            # return the character
            return ch

        # If the key was Esc, it could either be the single key
        # 'Escape', or part of a multicharacter sequence, such as 
        # the up arrow which is encoded as Esc+[+A
        
        # Semi-recursive call to get the next char to see if it is 
        # part of an escape sequence, or the character Esc itself
        # adds them to a buffer, in case they need to be readded
        # to the queue
        buf = [self.get_key_or_none()]

        # Probably an arrow key
        if buf[-1] == '[':

            # Same deal, check to see if the next key in the 
            # queue creates a directional sequence or is just
            # a poorly polled, unlikely sequence
            buf.append(self.get_key_or_none())
            if buf[-1] in self.direc:
                
                # Directional key. Look up and return which direction 
                return self.direc[buf[-1]]
        
        # Else it was another sequence; readd the misread chars
        # and return the original 'Esc'
        return self.queue_and_return(ch, buf)

    def queue_and_return(self, ch, buf):
        """
            Re-adds characters that were accidentally read in anticipation
            of a multicharacter escape sequence, and returns the original
            character
            :param ch: str - the original character read
            :param buf: [str] - the misread keys, possibly None's
            :return: str - original character read
        """
        for char in buf[::-1]:
            if char:
                self._deque.appendleft(char)
        return ch

mac_keys = {
    1: 'ctrl+a',
    2: 'ctrl+b',
    3: 'ctrl+c',
    4: 'ctrl+d',
    5: 'ctrl+e',
    6: 'ctrl+f',
    7: 'ctrl+g',
    8: 'ctrl+h',
    9: 'tab',
    10: 'enter',
    11: 'ctrl+k',
    12: 'ctrl+l',
    13: 'ctrl+m',
    14: 'ctrl+n',
    15: 'ctrl+o',
    16: 'ctrl+p',
    17: 'ctrl+q',
    18: 'ctrl+r',
    19: 'ctrl+s',
    20: 'ctrl+t',
    22: 'ctrl+u',
    23: 'ctrl+w',
    24: 'ctrl+x',
    25: 'ctrl+y',
    26: 'ctrl+z',
    27: 'esc',
    28: 'ctrl+/',
    29: 'ctrl+5',
    30: 'ctrl+6',
    31: 'ctrl+7',
    32: ' ',
    33: '!',
    34: '"',
    35: '#',
    36: '$',
    37: '%',
    38: '&',
    39: "'",
    40: '(',
    41: ')',
    42: '*',
    43: '+',
    44: ',',
    45: '-',
    46: '.',
    47: '/',
    48: '0',
    49: '1',
    50: '2',
    51: '3',
    52: '4',
    53: '5',
    54: '6',
    55: '7',
    56: '8',
    57: '9',
    58: ':',
    59: ';',
    60: '<',
    61: '=',
    62: '>',
    63: '?',
    64: '@',
    65: 'A',
    66: 'B',
    67: 'C',
    68: 'D',
    69: 'E',
    70: 'F',
    71: 'G',
    72: 'H',
    73: 'I',
    74: 'J',
    75: 'K',
    76: 'L',
    77: 'M',
    78: 'N',
    79: 'O',
    80: 'P',
    81: 'Q',
    82: 'R',
    83: 'S',
    84: 'T',
    85: 'U',
    86: 'V',
    87: 'W',
    88: 'X',
    89: 'Y',
    90: 'Z',
    91: '[',
    92: '\\',
    93: ']',
    94: '^',
    95: '_',
    96: '`',
    97: 'a',
    98: 'b',
    99: 'c',
    100: 'd',
    101: 'e',
    102: 'f',
    103: 'g',
    104: 'h',
    105: 'i',
    106: 'j',
    107: 'k',
    108: 'l',
    109: 'm',
    110: 'n',
    111: 'o',
    112: 'p',
    113: 'q',
    114: 'r',
    115: 's',
    116: 't',
    117: 'u',
    118: 'v',
    119: 'w',
    120: 'x',
    121: 'y',
    122: 'z',
    123: '{',
    124: '|',
    125: '}',
    126: '~',
    127: 'delete',
    # these are hacks, so that they are in the dictionary
    # these codes should not be used
    128: "up",
    129: "down",
    130: "right",
    131: "left"
}

mac_direc = {
        'A': 'up',
        'B': 'down',
        'C': 'right',
        'D': 'left'
        }
