from io import StringIO
from mock import patch
import pytest

from peacock import Peacock, interact, keyboard, format, Mode, ModeError
from peacock.interact import _BufferInteract

def test_format():
    assert format("No peacocks here") == "No peacocks here"
    assert format("Blue {|blue}", 5) == "Blue \033[34;m5\033[0;m"
    assert format("normal fmt: {}", "hello") == "normal fmt: hello"

    format_string = format("this text is blue, bold and negative: "
                           "{:.3f|blue,bold;negative}, while this is "
                           "magenta on yellow: {|magenta;yellow}", 1/3, "random_text")
    should_be = ("this text is blue, bold and negative: "
                 "\033[34;1;7;m{:.3f}\033[0;m, while this is "
                 "magenta on yellow: \033[35;43;m{}\033[0;m".format(1/3, "random_text"))
    
    assert format_string == should_be

@pytest.fixture(scope='module')
@patch("peacock.peacock.peacock.InteractANSIMac")
@patch("peacock.peacock.peacock.MacKeyboard")
def _pck(mock_keyboard, mock_interact, request):
    mac = mock_keyboard.return_value
    out = StringIO()
    mock_interact.return_value = _BufferInteract(None, out, 120)
    mac.keys = keys
    mac.get_key_or_none.return_value = None    
    p = Peacock(out=out, debug=True)
    def fin():
        p.stop()
    request.addfinalizer(fin)
    return p
   
@pytest.fixture
def pck(_pck):
    _pck.reset()
    assert len(_pck._buffer) == 1
    assert _pck._buffer[0] == ''
    assert _pck._x == _pck._y == 0
    return _pck

@pytest.fixture
def hello_pck(pck):
    pck.write("hello\nworld")
    assert pck._x == pck.interact.x == 5 
    assert pck._y == pck.interact.y == 1
    pck.move_cursor(0, -3)
    assert pck.out.getvalue() == "hello\nworld"
    assert pck._buffer[0] == "hello"
    assert pck._buffer[1] == "world"
    assert pck.trailing_output() == "rld"
    assert pck._x == pck.interact.x == 2 
    assert pck._y == pck.interact.y == 1
    return pck

@pytest.fixture
def long_pck(pck):
    pck.write("hello\nworld\nmonkey\ndishwasher\nbrains")
    pck.move_cursor(-1, -3)
    assert pck._x == pck.interact.x == 3 
    assert pck._y == pck.interact.y == 3
    return pck

def test_add_mode(hello_pck):
    assert "normal" not in hello_pck.modes
    normal = Mode("normal", hello_pck.keyboard)
    hello_pck.add_mode(normal)
    assert "normal" in hello_pck.modes

def test_add_handler_raises_error_for_unregistered_mode(hello_pck):
    with pytest.raises(ModeError):
        @hello_pck.on("enter", mode="normal")
        def fun():
            pass
    
def test_on(hello_pck):
    normal = Mode("normal", hello_pck.keyboard)
    hello_pck.add_mode(normal)
    @hello_pck.on("enter", mode="normal")
    def fun():
        pass
    assert "enter" in normal.handlers

def test_set_mode(hello_pck):
    assert hello_pck.mode.name == "insert"
    assert "ctrl+p" not in hello_pck.mode.handlers
    ctrl_p_mode = Mode("ctrlpmode", hello_pck.keyboard)
    hello_pck.add_mode(ctrl_p_mode)
    @hello_pck.on("ctrl+p", mode=ctrl_p_mode.name)
    def handler():
        pass
    hello_pck.set_mode(ctrl_p_mode.name)
    assert hello_pck.mode.name == ctrl_p_mode.name
    assert "ctrl+p" in hello_pck.mode.handlers

def test_insert_handle(hello_pck):
    hello_pck.handle("delete")
    assert hello_pck.out.getvalue() == "hello\nwrld"
    assert (hello_pck._x, hello_pck._y) == (1, 1)
    hello_pck.handle("up")
    assert (hello_pck._x, hello_pck._y) == (1, 0)
    hello_pck.handle("up")
    assert (hello_pck._x, hello_pck._y) == (1, 0)
    hello_pck.handle("down")
    assert (hello_pck._x, hello_pck._y) == (1, 1)
    hello_pck.handle("down")
    assert (hello_pck._x, hello_pck._y) == (1, 1)
    hello_pck.handle("left")
    assert (hello_pck._x, hello_pck._y) == (0, 1)
    hello_pck.handle("left")
    assert (hello_pck._x, hello_pck._y) == (0, 1)
    hello_pck.handle("right")
    assert (hello_pck._x, hello_pck._y) == (1, 1)
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    assert (hello_pck._x, hello_pck._y) == (4, 1)
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    assert (hello_pck._x, hello_pck._y) == (4, 1)
    hello_pck.handle("enter")
    assert hello_pck.out.getvalue() == "hello\nwrld\n"
    assert (hello_pck._x, hello_pck._y) == (0, 2)

def test_handle_arrows_read_mode(hello_pck):
    assert (hello_pck._x, hello_pck._y) == (2, 1)
    hello_pck.set_mode("read")
    hello_pck.handle("up")
    assert (hello_pck._x, hello_pck._y) == (2, 1)
    hello_pck.handle("down")
    assert (hello_pck._x, hello_pck._y) == (2, 1)

def test_stop(pck):
    assert pck.running
    pck.stop()
    assert not pck.running
    assert pck.keyboard.stop.called

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

