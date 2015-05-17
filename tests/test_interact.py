import pytest
from peacock import keyboard, interact 
from unittest.mock import patch, MagicMock
from io import StringIO

@patch("peacock.keyboard.termios")
@patch("peacock.keyboard.setcbreak")
@patch("peacock.keyboard.sys")
def test_keybaord(mock_sys, mock_setcbreak, mock_termios):
    mock_stdin = StringIO("a A \033 \033[A \3 3 ; : \\ ! > 0 9 ")
    mock_sys.stdin = mock_stdin
    keys = ["a", "A", "esc", "up", "ctrl+c", "3", 
            ";", ":", "\\",  "!", ">", "0", "9"]
    board = keyboard.MacKeyboard()
    for key in keys:
        assert board.get_key_or_none() == key
        assert board.get_key_or_none() == " " 
    assert board.get_key_or_none() == None
    board.stop()


################################################################################
################################# FIXTURES #####################################
################################################################################
@pytest.fixture
def buf():
    buf = interact._BufferInteract(None, StringIO(), 120)
    buf.write("hello\nworld") 
    assert buf.out.getvalue() == "hello\nworld"
    assert (buf.x, buf.y) == (5, 1)
    buf.move_cursor(0, -3)
    assert (buf.x, buf.y) == (2, 1)
    return buf

@pytest.fixture
def long_buf():
    buf = interact._BufferInteract(None, StringIO(), 120)
    buf.write("hello\nworld\nmonkey\ndishwasher\nbrains")
    buf.move_cursor(-1, -3)
    assert (buf.x, buf.y) == (3, 3) 
    return buf

################################################################################
##############################  IO METHODS  ####################################
################################################################################
def test_reset(buf):
    assert (buf.x, buf.y) == (2, 1)
    assert buf.out.getvalue() == "hello\nworld"
    assert buf._buffer == ["hello", "world"]
    buf.reset()
    assert (buf.x, buf.y) == (0, 0)
    assert buf.out.getvalue() == ""
    assert buf._buffer == [""]

def test_write(buf):
    buf.write("pancakes\nbananas")
    assert buf.out.getvalue() == "hello\nwopancakes\nbananasrld"
    assert (buf.x, buf.y) == (7, 2) 
    buf.move_cursor(rows=-1, cols=-2)
    assert (buf.x, buf.y) == (5, 1) 
    
    buf.write("\npancakes\nbananas")
    assert buf._buffer == ["hello", "wopan", "pancakes", "bananascakes", "bananasrld"]

    assert buf.out.getvalue()== "hello\nwopan\npancakes\nbananascakes\nbananasrld"
    assert (buf.x, buf.y) == (7, 3) 

def test_enter_insert_write(buf):
    buf.write("\n")
    assert buf.out.getvalue() == "hello\nwo\nrld"
    assert buf._buffer == ["hello", "wo", "rld"]
    assert (buf.x, buf.y) == (0, 2) 
    
    buf.delete(4) 
    assert buf._buffer == ["hellorld"]
    assert buf.out.getvalue() == "hellorld"
    assert (buf.x, buf.y) == (5, 0) 
    buf.move_cursor_to_x(3)
    assert (buf.x, buf.y) == (3, 0) 
    buf.write("\n")
    assert buf.out.getvalue() == "hel\nlorld"
    assert buf._buffer == ["hel", "lorld"]
    assert (buf.x, buf.y) == (0, 1) 


def test_multiline_insert_write(buf):
    buf.write("muffin\ntop")
    assert buf.out.getvalue() == "hello\nwomuffin\ntoprld"
    assert buf._buffer == ["hello", "womuffin", "toprld"]
    assert (buf.x, buf.y) == (3, 2) 
    buf.move_cursor_to_eol()
    assert (buf.x, buf.y) == (6, 2) 
    buf.write("s\n")
    assert buf.out.getvalue() == "hello\nwomuffin\ntoprlds\n"
    assert buf._buffer == ["hello", "womuffin", "toprlds", ""]
    assert (buf.x, buf.y) == (0, 3) 


def test_clear_line(buf):
    buf.delete_line()
    assert buf.trailing_output() == ""
    assert (buf.x, buf.y) == (2, 1) 
    assert buf.out.getvalue() == "hello\nwo"
    assert buf._buffer == ["hello", "wo"]


def test_simple_delete_line(buf):
    buf.move_cursor_to_x(3)
    assert (buf.x, buf.y) == (3, 1)
    buf.delete_line()
    assert buf._buffer == ["hello", "wor"]
    assert buf.out.getvalue() == 'hello\nwor'

def test_multiline_delete_line(buf):
    buf.move_cursor(-1, 1)
    assert buf.x == 3
    assert buf.y == 0
    assert buf.out.getvalue() == 'hello\nworld'
    buf.delete_line()
    assert buf.out.getvalue() == 'hel\nworld'

    
def test_medium_delete(buf):
    buf.move_cursor(-1, 2)    
    assert buf.out.getvalue() == "hello\nworld"
    assert buf._buffer == ["hello", "world"]
    assert (buf.x, buf.y) == (4, 0)
    buf.delete(3)
    assert buf.out.getvalue() == "ho\nworld"
    assert buf._buffer == ["ho", "world"]
    assert (buf.x, buf.y) == (1, 0)
    buf.move_cursor(1, 2)    
    assert (buf.x, buf.y) == (3, 1)
    buf.delete(2)
    assert buf.out.getvalue() == "ho\nwld"
    assert buf._buffer == ["ho", "wld"]


def test_multiline_delete(buf):
    buf.delete(4)
    assert buf.out.getvalue() == "hellrld"
    assert buf._buffer == ["hellrld"]
    assert buf.trailing_output() == "rld"
    assert (buf.x, buf.y) == (4, 0)
    buf.delete(25)
    assert (buf.x, buf.y) == (0, 0)
    assert buf.out.getvalue() == "rld"
    assert buf._buffer == ["rld"]
    buf.write("hello\nwo")
    assert (buf.x, buf.y) == (2, 1)
    assert buf.out.getvalue() == "hello\nworld"
    assert buf._buffer == ["hello", "world"]
    buf.delete(4)
    assert (buf.x, buf.y) == (4, 0)
    assert buf.out.getvalue() == "hellrld"

def test_newline_fuckery(buf):
    buf.reset()
    buf.write("s")
    assert buf.out.getvalue() == "s"
    assert buf._buffer == ["s"]
    assert buf.trailing_output() == ""
    assert (buf.x, buf.y) == (1, 0)
    buf.move_cursor(cols=-1)
    assert buf._buffer == ["s"]
    assert buf.trailing_output() == "s"
    assert (buf.x, buf.y) == (0, 0)
    buf.write("\n")
    assert buf.out.getvalue() == "\ns"
    assert buf._buffer == ["", "s"]
    assert buf.trailing_output() == "s"
    assert (buf.x, buf.y) == (0, 1)
    buf.move_cursor(rows=-1)
    assert buf.out.getvalue() == "\ns"
    assert buf._buffer == ["", "s"]
    assert buf.trailing_output() == "\ns"
    assert (buf.x, buf.y) == (0, 0)
    assert buf.trailing_output() == "\ns"
    buf.write("\n")
    assert buf.trailing_output() == "\ns"
    assert buf.out.getvalue() == "\n\ns"
    assert (buf.x, buf.y) == (0, 1)
    assert buf._buffer == ["", "", "s"]

################################################################################
############################### CURSOR METHODS #################################
################################################################################
def test_move_cursor(buf):
    assert (buf.x, buf.y) == (2, 1)
    buf.move_cursor(-1, -1)
    assert (buf.x, buf.y) == (1, 0) 
    buf.move_cursor(0, -100)
    assert (buf.x, buf.y) == (0, 0) 
    buf.move_cursor(100, 100)
    assert (buf.x, buf.y) == (5, 1) 

def test_move_cursor_to(long_buf):
    assert (long_buf.x, long_buf.y) == (3, 3) 
    long_buf.move_cursor_to(4, 4)
    assert (long_buf.x, long_buf.y) == (4, 4) 
    long_buf.move_cursor_to(0, -100)
    assert (long_buf.x, long_buf.y) == (0, 4) 
    long_buf.move_cursor_to(100, 100)
    assert (long_buf.x, long_buf.y) == (6, 4) 

def test_move_cursor_to_x(buf):
    assert (buf.x, buf.y) == (2, 1)
    buf.move_cursor_to_x(3)
    assert (buf.x, buf.y) == (3, 1)
    buf.move_cursor_to_x(1000)
    assert (buf.x, buf.y) == (5, 1)
    buf.move_cursor_to_x(-1000)
    assert (buf.x, buf.y) == (0, 1)

def test_move_cursor_to_eol(buf):
    assert (buf.x, buf.y) == (2, 1)
    buf.move_cursor_to_eol()
    assert (buf.x, buf.y) == (5, 1)
    buf.move_cursor_to_eol(-1)
    assert (buf.x, buf.y) == (5, 0)

def test_move_cursor_to_beginning(buf):
    assert (buf.x, buf.y) == (2, 1)
    buf.move_cursor_to_beginning()
    assert (buf.x, buf.y) == (0, 1)
    buf.move_cursor_to_beginning(-1)
    assert (buf.x, buf.y) == (0, 0)

def test_move_cursor_to_eof(long_buf, buf):
    assert (buf.x, buf.y) == (2, 1)
    buf.move_cursor_to_eof()
    assert (buf.x, buf.y) == (5, 1)
    assert (long_buf.x, long_buf.y) == (3, 3)
    long_buf.move_cursor_to_eof()
    assert (long_buf.x, long_buf.y) == (6, 4)

def test_save_cursor(buf):
    assert (buf.x, buf.y) == (2, 1)
    restore = buf.save_cursor()
    buf.write("elephant\n")
    buf.move_cursor(100, 100)
    assert buf.out.getvalue() == "hello\nwoelephant\nrld"
    assert buf._buffer == ["hello", "woelephant", "rld"]
    assert (buf.x, buf.y) == (3, 2)
    restore()
    assert (buf.x, buf.y) == (2, 1)

################################################################################
############################## UTILITY METHODS #################################
################################################################################
def test_calculate_ending_position(long_buf):
    assert long_buf._calculate_ending_position(0) == (3, 3)  
    assert long_buf._calculate_ending_position(2) == (1, 3)  
    assert long_buf._calculate_ending_position(16) == (0, 1)  
    assert long_buf._calculate_ending_position(9) == (1, 2)
    long_buf.move_cursor_to_beginning()
    assert long_buf._calculate_ending_position(1) == (6, 2) 

