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


@pytest.fixture
def buf():
    buf = interact._BufferInteract(None, StringIO(), 120)
    buf.write("hello\nworld")
    return buf


def test_write(buf):
    assert buf.out.getvalue() == "hello\nworld"
    assert buf.x == 5
    assert buf.y == 1
    buf.write("pancakes\nbananas")
    assert buf.out.getvalue() == "hello\nworldpancakes\nbananas"
    assert buf.x == 7
    assert buf.y == 2
    buf.move_cursor_absolute(x=5, y=1)
    buf.write("\npancakes\nbananas")
    assert buf.out.getvalue()[10:] == "hello\nworld\npancakes\nbananas"[10:]
    assert buf.x == 7
    assert buf.y == 3


def test_array(buf):
    arr = buf.array
    assert len(arr) == 2
    assert arr[0] == 'hello'
    assert arr[1] == 'world'


def test_move_cursor(buf):
    assert buf.x == 5
    assert buf.y == 1
    buf.move_cursor(-1, -100)
    assert buf.x == buf.y == 0
    buf.move_cursor(0, 100)
    assert buf.x == 5
    assert buf.y == 0


def test_move_cursor_to_x(buf):
    assert buf.x == 5
    assert buf.y == 1
    buf.move_cursor_to_x(3, 120)
    assert buf.x == 3


def test_simple_delete_line(buf):
    buf.move_cursor_to_x(3, 120)
    assert buf.x == 3
    assert buf.y == 1
    buf.delete_line()
    assert buf.out.getvalue() == 'hello\nwor'


def test_multiline_delete_line(buf):
    buf.move_cursor(-1, -2)
    assert buf.x == 3
    assert buf.y == 0
    assert buf.out.getvalue() == 'hello\nworld'
    buf.delete_line()
    assert buf.out.getvalue() == 'hel\nworld'


# def test_cursor_correct(buf):
#     assert buf.x == 5
#     assert buf.y == 1
#     buf.write(" monkey", trailing=" elephant\nfountain")
#     assert buf.out.getvalue() == "hello\nworld monkey elephant\nfountain"
#     assert buf.y == 1
#     assert buf.x == 12
#     buf.write(" brains", trailing=" buttons")
#     assert buf.out.getvalue() == "hello\nworld monkey brains buttonsain"
#     assert buf.y == 1
#     assert buf.x == 19
# 
# 
# def test_delete_lines(buf):
#     buf.write("\nmonkey\nelephant\nbrain")
#     assert buf.out.getvalue() == "hello\nworld\nmonkey\nelephant\nbrain"
#     assert buf.y == 4 
#     buf.replace_lines_with_buffer(["pink"], up=3)
#     assert buf.out.getvalue() == "hello\npink\n\n\n"
#     assert buf.y == 1 
# 
# def test_cursor_correct_newlines(buf):
#     assert buf.x == 5
#     assert buf.y == 1
#     buf.write(" pancakes", trailing="\n")
#     assert buf.x == 14
#     assert buf.y == 1
