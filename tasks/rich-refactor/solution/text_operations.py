"""Text sizing and fitting operations extracted from Text class.

This module contains functions for manipulating Text dimensions:
truncation, padding, alignment, and length management.
"""

from typing import TYPE_CHECKING, Optional

from .cells import cell_len, set_cell_size

if TYPE_CHECKING:
    from .text import Text
    from .console import OverflowMethod

DEFAULT_OVERFLOW: "OverflowMethod" = "fold"


def truncate(
    text: "Text",
    max_width: int,
    *,
    overflow: Optional["OverflowMethod"] = None,
    pad: bool = False,
) -> None:
    """Truncate text if it is longer that a given width.

    Args:
        text: The Text instance to truncate.
        max_width (int): Maximum number of characters in text.
        overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". 
            Defaults to None, to use text.overflow.
        pad (bool, optional): Pad with spaces if the length is less than max_width. 
            Defaults to False.
    """
    _overflow = overflow or text.overflow or DEFAULT_OVERFLOW
    if _overflow != "ignore":
        length = cell_len(text.plain)
        if length > max_width:
            if _overflow == "ellipsis":
                text.plain = set_cell_size(text.plain, max_width - 1) + "…"
            else:
                text.plain = set_cell_size(text.plain, max_width)
        if pad and length < max_width:
            spaces = max_width - length
            text._text = [f"{text.plain}{' ' * spaces}"]
            text._length = len(text.plain)


def pad(text: "Text", count: int, character: str = " ") -> None:
    """Pad left and right with a given number of characters.

    Args:
        text: The Text instance to pad.
        count (int): Width of padding.
        character (str): The character to pad with. Must be a string of length 1.
    """
    assert len(character) == 1, "Character must be a string of length 1"
    if count:
        pad_characters = character * count
        text.plain = f"{pad_characters}{text.plain}{pad_characters}"
        # Import Span locally to avoid issues, or use the spans directly
        text._spans[:] = [
            span.move(count) for span in text._spans
        ]


def pad_left(text: "Text", count: int, character: str = " ") -> None:
    """Pad the left with a given character.

    Args:
        text: The Text instance to pad.
        count (int): Number of characters to pad.
        character (str, optional): Character to pad with. Defaults to " ".
    """
    assert len(character) == 1, "Character must be a string of length 1"
    if count:
        text.plain = f"{character * count}{text.plain}"
        text._spans[:] = [
            span.move(count) for span in text._spans
        ]


def pad_right(text: "Text", count: int, character: str = " ") -> None:
    """Pad the right with a given character.

    Args:
        text: The Text instance to pad.
        count (int): Number of characters to pad.
        character (str, optional): Character to pad with. Defaults to " ".
    """
    assert len(character) == 1, "Character must be a string of length 1"
    if count:
        text.plain = f"{text.plain}{character * count}"


def align(
    text: "Text",
    align_method: str,
    width: int,
    character: str = " ",
) -> None:
    """Align text to a given width.

    Args:
        text: The Text instance to align.
        align_method: One of "left", "center", or "right".
        width (int): Desired width.
        character (str, optional): Character to pad with. Defaults to " ".
    """
    truncate(text, width)
    excess_space = width - cell_len(text.plain)
    if excess_space:
        if align_method == "left":
            pad_right(text, excess_space, character)
        elif align_method == "center":
            left = excess_space // 2
            pad_left(text, left, character)
            pad_right(text, excess_space - left, character)
        else:
            pad_left(text, excess_space, character)


def set_length(text: "Text", new_length: int) -> None:
    """Set new length of the text, clipping or padding as required.

    Args:
        text: The Text instance to modify.
        new_length (int): The desired length.
    """
    length = len(text)
    if length != new_length:
        if length < new_length:
            pad_right(text, new_length - length)
        else:
            text.right_crop(length - new_length)
