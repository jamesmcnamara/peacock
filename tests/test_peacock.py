from io import StringIO
from mock import patch
import pytest

from peacock import Peacock, interact, keyboard, format
from peacock.interact import _BufferInteract
# from peacock.peacock import format
# from peacock.interact.interact import _BufferInteract

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
    mock_interact.return_value = _BufferInteract
    mac.keys.values.return_value.__contains__.return_value = True
    mac.get_key_or_none.return_value = None    
    p = Peacock(out=StringIO(), debug=True)
    def fin():
        p.stop()
    request.addfinalizer(fin)
    return p
   
@pytest.fixture
def pck(_pck):
    _pck.reset()
    _pck.out = StringIO()
    _pck.interact = _BufferInteract(None, _pck.out, _pck.line_length)
    assert len(_pck._buffer) == 1
    assert _pck._buffer[0].getvalue() == ''
    assert _pck._x == _pck._y == 0
    return _pck

@pytest.fixture
def hello_pck(pck):
    pck.write("hello\nworld")
    pck.move_cursor(0, -3)
    assert pck.out.getvalue() == "hello\nworld"
    assert pck.trailing_output == "rld"
    assert pck._x == pck.interact.x == 2 
    assert pck._y == pck.interact.y == 1
    return pck

def test_trailing_output(hello_pck):
    assert hello_pck.trailing_output == 'rld'

def test_simple_write(pck):
    assert pck.interact.off == 0
    pck.write("hello\nworld")
    assert pck.out.getvalue() == "hello\nworld"

def test_move_cursor(hello_pck):
    assert hello_pck._x == hello_pck.interact.x == 2
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.move_cursor(-1, -1)
    assert hello_pck._x == hello_pck.interact.x == 1 
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.move_cursor(0, -100)
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.move_cursor(100, 100)
    assert hello_pck._x == hello_pck.interact.x == 5
    assert hello_pck._y == hello_pck.interact.y == 1

def test_move_cursor_to_x(hello_pck):
    assert hello_pck._x == hello_pck.interact.x == 2
    hello_pck.move_cursor_to_x(3)
    assert hello_pck._x == hello_pck.interact.x == 3 
    hello_pck.move_cursor_to_x(0)
    assert hello_pck._x == hello_pck.interact.x == 0 
    hello_pck.move_cursor_to_x(1e9)
    assert hello_pck._x == hello_pck.interact.x == 5 

def test_move_cursor_to_eol(hello_pck):
    assert hello_pck._x == hello_pck.interact.x == 2
    assert hello_pck._y == hello_pck.interact.y == 1 
    hello_pck.move_cursor_to_eol()
    assert hello_pck._x == hello_pck.interact.x == 5 
    assert hello_pck._y == hello_pck.interact.y == 1 
    hello_pck.move_cursor_to_eol(-1)
    assert hello_pck._x == hello_pck.interact.x == 5 
    assert hello_pck._y == hello_pck.interact.y == 0 

def test_move_cursor_to_beginning(hello_pck):
    assert hello_pck._x == hello_pck.interact.x == 2
    assert hello_pck._y == hello_pck.interact.y == 1 
    hello_pck.move_cursor_to_beginning()
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 1 
    hello_pck.move_cursor_to_beginning(-1)
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 0 

def test_simple_insert_write(pck):
    assert pck.interact.off == 0
    pck.write("hello")
    assert pck._x == pck.interact.x
    assert pck._y == pck.interact.y    
    pck.move_cursor(0, -3)
    assert pck._x == 2
    assert pck.trailing_output == "llo"
    assert pck._x == pck.interact.x
    assert pck._y == pck.interact.y
    pck.write("xx")
    assert pck.out.getvalue() == "hexxllo"

def test_medium_insert_write(hello_pck):
    hello_pck.write("xx")
    assert hello_pck.out.getvalue() == "hello\nwoxxrld"
    hello_pck.move_cursor_to_eol(-1)
    hello_pck.write("s")
    assert hello_pck.out.getvalue() == "hellos\nwoxxrld"
    assert hello_pck._x == hello_pck.interact.x == 6 
    assert hello_pck._y == hello_pck.interact.y == 0 


def test_enter_insert_write(hello_pck):
    hello_pck.write("\n")
    assert hello_pck.out.getvalue() == "hello\nwo\nrld"
    assert hello_pck._x == hello_pck.interact.x == 0
    assert hello_pck._y == hello_pck.interact.y == 2

def test_multiline_insert_write(hello_pck):
    hello_pck.write("muffin\ntop")
    assert hello_pck.out.getvalue() == "hello\nwomuffin\ntoprld"
    assert hello_pck._x == hello_pck.interact.x == 3 
    assert hello_pck._y == hello_pck.interact.y == 2
    hello_pck.move_cursor_to_eol()
    assert hello_pck._x == hello_pck.interact.x == 6
    hello_pck.write("s\n")
    assert hello_pck.out.getvalue() == "hello\nwomuffin\ntoprlds\n"
    assert hello_pck._x == hello_pck.interact.x == 0 
    assert hello_pck._y == hello_pck.interact.y == 3
    assert hello_pck._buffer[2].getvalue() == 'toprlds'
    assert hello_pck._buffer[3].getvalue() == ''

def test_simple_buffer(pck):
    pck.write("hello\nworld")
    assert len(pck._buffer) == 2 
    assert pck._buffer[0].getvalue() == 'hello'
    assert pck._x == 5 
    assert pck._y == 1

def test_simple_insert_buffer(pck):
    pck.write("hello")
    pck._x = 2
    pck.write("xx")
    assert pck._buffer[0].getvalue() == "hexxllo"
    assert pck._x == 4 
    assert pck._y == 0

def test_medium_insert_buffer(hello_pck):
    hello_pck.write("xx")
    assert hello_pck._buffer[1].getvalue() == "woxxrld"
    assert hello_pck._x == 4
    assert hello_pck._y == 1

def test_multiline_insert_buffer(hello_pck):
    hello_pck.write("muffin\ntop")
    assert hello_pck._buffer[1].getvalue() == "womuffin"
    assert hello_pck._buffer[2].getvalue() == "toprld"
    assert hello_pck._x == 3 
    assert hello_pck._y == 2

def test_simple_delete_out(pck):
    pck.write("hello")
    assert pck._x == 5
    assert pck.out.getvalue() == 'hello'
    assert pck.interact.out is pck.out
    pck.delete(1)
    assert pck.out.getvalue() == 'hell '
    assert pck._x == 4 
    pck.move_cursor(0, -2)
    assert pck._x == pck.interact.x == 2
    assert pck.trailing_output == "ll"
    pck.delete(1)
    assert pck._x == pck.interact.x == 1 
    assert pck.out.getvalue() == 'hll  '
    pck.write("elp ")
    assert pck.out.getvalue() == 'help ll'
    assert pck._x == pck.interact.x == 5
    pck.delete(4)
    assert pck.out.getvalue() == 'hll    '
    assert pck._x == pck.interact.x == 1
    pck.delete(0)
    assert pck.out.getvalue() == 'hll    '
    assert pck._x == pck.interact.x == 1
    pck.delete(1)
    assert pck.out.getvalue() == 'll     '
    assert pck._x == pck.interact.x == 0



def test_simple_delete_buffer(pck):
    pck.write("hello")
    assert pck._x == pck.interact.x == 5
    pck.delete(1)
    assert pck._buffer[0].getvalue() == 'hell'
    assert pck._x == 4 
    pck.move_cursor(0, -2)
    assert pck._x == pck.interact.x == 2
    pck.delete(1)
    assert pck._x == pck.interact.x == 1 
    assert pck._buffer[0].getvalue() == 'hll'

def test_medium_delete_out(hello_pck):
    hello_pck.move_cursor(-1, 2)    
    assert hello_pck.out.getvalue() == "hello\nworld"
    assert hello_pck._x == hello_pck.interact.x == 4 
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.delete(3)
    assert hello_pck.out.getvalue() == "ho   \nworld"
    assert hello_pck._x == hello_pck.interact.x == 1 
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.move_cursor(1, 2)    
    assert hello_pck._x == hello_pck.interact.x == 3
    assert hello_pck._y == hello_pck.interact.y == 1
    hello_pck.delete(2)
    assert hello_pck.out.getvalue() == "ho   \nwld  "
    

def test_medium_delete_buffer(hello_pck):
    hello_pck.move_cursor(-1, 2)    
    assert hello_pck._buffer[0].getvalue() == "hello"
    assert hello_pck._buffer[1].getvalue() == "world"
    assert hello_pck._x == hello_pck.interact.x == 4 
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.delete(3)
    assert hello_pck._buffer[0].getvalue() == "ho"
    assert hello_pck._buffer[1].getvalue() == "world"
    assert hello_pck._x == hello_pck.interact.x == 1 
    assert hello_pck._y == hello_pck.interact.y == 0
      

def test_multiline_delete_out(hello_pck):
    hello_pck.delete(4)
    assert hello_pck.out.getvalue() == "hel  \nrld  "
    assert hello_pck.trailing_output == "\nrld"
    assert hello_pck._x == hello_pck.interact.x == 3
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.delete(25)
    assert hello_pck._x == hello_pck.interact.x == 0
    assert hello_pck._y == hello_pck.interact.y == 0
    assert hello_pck.out.getvalue() == "     \nrld  "

def test_multiline_delete_buffer(hello_pck):
    hello_pck.delete(4)
    assert hello_pck._buffer[0].getvalue() == "hel"
    assert hello_pck._buffer[1].getvalue() == "rld"
    assert hello_pck._x == hello_pck.interact.x == 3
    assert hello_pck._y == hello_pck.interact.y == 0
    hello_pck.delete(25)
    assert hello_pck._x == hello_pck.interact.x == 0
    assert hello_pck._y == hello_pck.interact.y == 0
    assert hello_pck._buffer[0].getvalue() == ""
    assert hello_pck._buffer[1].getvalue() == "rld"

def test_handle(hello_pck):
    hello_pck.handle("delete")
    assert hello_pck.out.getvalue() == "hello\nwrld "
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

def test_stop(pck):
    assert pck.running
    pck.stop()
    assert not pck.running
    assert pck.keyboard.stop.called




