import pytest
from unittest.mock import MagicMock
from peacock import Mode, ModeError

@pytest.fixture
def normal():
    keyboard = MagicMock()
    keyboard.keys = keys
    normal = Mode("normal", keyboard)
    return normal

def test_on_raises_on_bad_keys(normal):
    with pytest.raises(ValueError):
        @normal.on("garbage key")   
        def handler():
            pass

def test_on(normal):
    assert normal.handlers == {}
    @normal.on("enter")
    def handler():
        pass
    assert len(normal.handlers) == 1
    assert "enter" in normal.handlers

def test_handle(normal):
    with pytest.raises(KeyError):
        normal.handle("enter", None)
    @normal.on("enter")
    def return_x(app, curr_line, x):
        return x
    mock_app = MagicMock()
    assert normal.handle("enter", mock_app) == mock_app._x
    mock_app._buffer.__getitem__.assert_called_with(mock_app._y)

keys = {
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

