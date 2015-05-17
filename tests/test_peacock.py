from io import StringIO
from mock import patch
import pytest

from peacock import Peacock, interact, keyboard, format, Mode
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
@patch("peacock.peacock.InteractANSIMac")
@patch("peacock.peacock.MacKeyboard")
def _pck(mock_keyboard, mock_interact, request):
    mac = mock_keyboard.return_value
    out = StringIO()
    mock_interact.return_value = _BufferInteract(None, out, 120)
    mac.keys.values.return_value.__contains__.return_value = True
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


def test_handle(hello_pck):
    hello_pck.handle("delete")
    assert hello_pck.out.getvalue() == "hello\nwrld"
    assert hello_pck._x == hello_pck.interact.x == 1
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("up")
    assert hello_pck._x == hello_pck.interact.x == 1
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.handle("up")
    assert hello_pck._x == hello_pck.interact.x == 1
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.handle("down")
    assert hello_pck._x == hello_pck.interact.x == 1
    assert hello_pck._y == hello_pck.interact.y == 1 
    hello_pck.handle("down")
    assert hello_pck._x == hello_pck.interact.x == 1
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("left")
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("left")
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("right")
    assert hello_pck._x == hello_pck.interact.x == 1 
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    assert hello_pck._x == hello_pck.interact.x == 4 
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    hello_pck.handle("right")
    assert hello_pck._x == hello_pck.interact.x == 4 
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.handle("enter")
    assert hello_pck.out.getvalue() == "hello\nwrld\n"
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 2


# def test_cursor_correct(pck):
#     assert (5, 1) == pck._cursor_correction("hello\nworld")
#     assert (4, 7) == pck._cursor_correction("this\nis\nthe\nway\n"
#                                            "the\nworld\nwill\nend")

def test_stop(pck):
    assert pck.running
    pck.stop()
    assert not pck.running
    assert pck.keyboard.stop.called




