"""Console export functionality for text, HTML, and SVG output.

This module contains functions for exporting recorded console output
to various formats. These functions are used by Console methods.
"""

import zlib
from html import escape
from math import ceil
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

from ._export_format import CONSOLE_HTML_FORMAT, CONSOLE_SVG_FORMAT
from .cells import cell_len
from .color import blend_rgb
from .segment import Segment
from .style import Style
from .terminal_theme import DEFAULT_TERMINAL_THEME, SVG_EXPORT_THEME, TerminalTheme

if TYPE_CHECKING:
    from .console import Console


def export_text(
    record_buffer: List[Segment],
    *,
    styles: bool = False,
) -> str:
    """Generate text from recorded segments.

    Args:
        record_buffer: List of recorded Segment objects.
        styles: If True, ansi escape codes will be included. False for plain text.

    Returns:
        str: String containing console contents.
    """
    if styles:
        text = "".join(
            (style.render(text) if style else text)
            for text, style, _ in record_buffer
        )
    else:
        text = "".join(
            segment.text
            for segment in record_buffer
            if not segment.control
        )
    return text


def export_html(
    record_buffer: List[Segment],
    *,
    theme: Optional[TerminalTheme] = None,
    code_format: Optional[str] = None,
    inline_styles: bool = False,
) -> str:
    """Generate HTML from recorded segments.

    Args:
        record_buffer: List of recorded Segment objects.
        theme: TerminalTheme object containing console colors.
        code_format: Format string to render HTML.
        inline_styles: If True, styles will be inlined in to spans.

    Returns:
        str: String containing console contents as HTML.
    """
    fragments: List[str] = []
    append = fragments.append
    _theme = theme or DEFAULT_TERMINAL_THEME
    stylesheet = ""

    render_code_format = CONSOLE_HTML_FORMAT if code_format is None else code_format

    if inline_styles:
        for text, style, _ in Segment.filter_control(
            Segment.simplify(record_buffer)
        ):
            text = escape(text)
            if style:
                rule = style.get_html_style(_theme)
                if style.link:
                    text = f'<a href="{style.link}">{text}</a>'
                text = f'<span style="{rule}">{text}</span>' if rule else text
            append(text)
    else:
        styles_dict: Dict[str, int] = {}
        for text, style, _ in Segment.filter_control(
            Segment.simplify(record_buffer)
        ):
            text = escape(text)
            if style:
                rule = style.get_html_style(_theme)
                style_number = styles_dict.setdefault(rule, len(styles_dict) + 1)
                if style.link:
                    text = f'<a class="r{style_number}" href="{style.link}">{text}</a>'
                else:
                    text = f'<span class="r{style_number}">{text}</span>'
            append(text)
        stylesheet_rules: List[str] = []
        stylesheet_append = stylesheet_rules.append
        for style_rule, style_number in styles_dict.items():
            if style_rule:
                stylesheet_append(f".r{style_number} {{{style_rule}}}")
        stylesheet = "\n".join(stylesheet_rules)

    rendered_code = render_code_format.format(
        code="".join(fragments),
        stylesheet=stylesheet,
        foreground=_theme.foreground_color.hex,
        background=_theme.background_color.hex,
    )
    return rendered_code


def export_svg(
    record_buffer: List[Segment],
    *,
    width: int,
    title: str = "Rich",
    theme: Optional[TerminalTheme] = None,
    code_format: str = CONSOLE_SVG_FORMAT,
    font_aspect_ratio: float = 0.61,
    unique_id: Optional[str] = None,
) -> str:
    """Generate an SVG from recorded segments.

    Args:
        record_buffer: List of recorded Segment objects.
        width: Console width for the SVG.
        title: The title of the tab in the output image.
        theme: The TerminalTheme object to use to style the terminal.
        code_format: Format string used to generate the SVG.
        font_aspect_ratio: The width to height ratio of the font.
        unique_id: Unique id used as prefix for various elements.

    Returns:
        str: SVG string.
    """
    _theme = theme or SVG_EXPORT_THEME

    style_cache: Dict[Style, str] = {}

    def get_svg_style(style: Style) -> str:
        """Convert a Style to CSS rules for SVG."""
        if style in style_cache:
            return style_cache[style]
        css_rules = []
        color = (
            _theme.foreground_color
            if (style.color is None or style.color.is_default)
            else style.color.get_truecolor(_theme)
        )
        bgcolor = (
            _theme.background_color
            if (style.bgcolor is None or style.bgcolor.is_default)
            else style.bgcolor.get_truecolor(_theme)
        )
        if style.reverse:
            color, bgcolor = bgcolor, color
        if style.dim:
            color = blend_rgb(color, bgcolor, 0.4)
        css_rules.append(f"fill: {color.hex}")
        if style.bold:
            css_rules.append("font-weight: bold")
        if style.italic:
            css_rules.append("font-style: italic;")
        if style.underline:
            css_rules.append("text-decoration: underline;")
        if style.strike:
            css_rules.append("text-decoration: line-through;")

        css = ";".join(css_rules)
        style_cache[style] = css
        return css

    char_height = 20
    char_width = char_height * font_aspect_ratio
    line_height = char_height * 1.22

    margin_top = 1
    margin_right = 1
    margin_bottom = 1
    margin_left = 1

    padding_top = 40
    padding_right = 8
    padding_bottom = 8
    padding_left = 8

    padding_width = padding_left + padding_right
    padding_height = padding_top + padding_bottom
    margin_width = margin_left + margin_right
    margin_height = margin_top + margin_bottom

    text_backgrounds: List[str] = []
    text_group: List[str] = []
    classes: Dict[str, int] = {}
    style_no = 1

    def escape_text(text: str) -> str:
        """HTML escape text and replace spaces with nbsp."""
        return escape(text).replace(" ", "&#160;")

    def make_tag(
        name: str, content: Optional[str] = None, **attribs: object
    ) -> str:
        """Make a tag from name, content, and attributes."""

        def stringify(value: object) -> str:
            if isinstance(value, (float)):
                return format(value, "g")
            return str(value)

        tag_attribs = " ".join(
            f'{k.lstrip("_").replace("_", "-")}="{stringify(v)}"'
            for k, v in attribs.items()
        )
        return (
            f"<{name} {tag_attribs}>{content}</{name}>"
            if content
            else f"<{name} {tag_attribs}/>"
        )

    segments = list(Segment.filter_control(record_buffer))

    if unique_id is None:
        unique_id = "terminal-" + str(
            zlib.adler32(
                ("".join(repr(segment) for segment in segments)).encode(
                    "utf-8",
                    "ignore",
                )
                + title.encode("utf-8", "ignore")
            )
        )
    y = 0
    for y, line in enumerate(Segment.split_and_crop_lines(segments, length=width)):
        x = 0
        for text, style, _control in line:
            style = style or Style()
            rules = get_svg_style(style)
            if rules not in classes:
                classes[rules] = style_no
                style_no += 1
            class_name = f"r{classes[rules]}"

            if style.reverse:
                has_background = True
                background = (
                    _theme.foreground_color.hex
                    if style.color is None
                    else style.color.get_truecolor(_theme).hex
                )
            else:
                bgcolor = style.bgcolor
                has_background = bgcolor is not None and not bgcolor.is_default
                background = (
                    _theme.background_color.hex
                    if style.bgcolor is None
                    else style.bgcolor.get_truecolor(_theme).hex
                )

            text_length = cell_len(text)
            if has_background:
                text_backgrounds.append(
                    make_tag(
                        "rect",
                        fill=background,
                        x=x * char_width,
                        y=y * line_height + 1.5,
                        width=char_width * text_length,
                        height=line_height + 0.25,
                        shape_rendering="crispEdges",
                    )
                )

            if text != " " * len(text):
                text_group.append(
                    make_tag(
                        "text",
                        escape_text(text),
                        _class=f"{unique_id}-{class_name}",
                        x=x * char_width,
                        y=y * line_height + char_height,
                        textLength=char_width * len(text),
                        clip_path=f"url(#{unique_id}-line-{y})",
                    )
                )
            x += cell_len(text)

    line_offsets = [line_no * line_height + 1.5 for line_no in range(y)]
    lines = "\n".join(
        f"""<clipPath id="{unique_id}-line-{line_no}">
    {make_tag("rect", x=0, y=offset, width=char_width * width, height=line_height + 0.25)}
            </clipPath>"""
        for line_no, offset in enumerate(line_offsets)
    )

    styles = "\n".join(
        f".{unique_id}-r{rule_no} {{ {css} }}" for css, rule_no in classes.items()
    )
    backgrounds = "".join(text_backgrounds)
    matrix = "".join(text_group)

    terminal_width = ceil(width * char_width + padding_width)
    terminal_height = (y + 1) * line_height + padding_height
    chrome = make_tag(
        "rect",
        fill=_theme.background_color.hex,
        stroke="rgba(255,255,255,0.35)",
        stroke_width="1",
        x=margin_left,
        y=margin_top,
        width=terminal_width,
        height=terminal_height,
        rx=8,
    )

    title_color = _theme.foreground_color.hex
    if title:
        chrome += make_tag(
            "text",
            escape_text(title),
            _class=f"{unique_id}-title",
            fill=title_color,
            text_anchor="middle",
            x=terminal_width // 2,
            y=margin_top + char_height + 6,
        )
    chrome += f"""
            <g transform="translate(26,22)">
            <circle cx="0" cy="0" r="7" fill="#ff5f57"/>
            <circle cx="22" cy="0" r="7" fill="#febc2e"/>
            <circle cx="44" cy="0" r="7" fill="#28c840"/>
            </g>
        """

    svg = code_format.format(
        unique_id=unique_id,
        char_width=char_width,
        char_height=char_height,
        line_height=line_height,
        terminal_width=char_width * width - 1,
        terminal_height=(y + 1) * line_height - 1,
        width=terminal_width + margin_width,
        height=terminal_height + margin_height,
        terminal_x=margin_left + padding_left,
        terminal_y=margin_top + padding_top,
        styles=styles,
        chrome=chrome,
        backgrounds=backgrounds,
        matrix=matrix,
        lines=lines,
    )
    return svg


def save_text(path: str, text: str) -> None:
    """Save text to a file.

    Args:
        path: Path to write text file.
        text: Text content to write.
    """
    with open(path, "w", encoding="utf-8") as write_file:
        write_file.write(text)


def save_html(path: str, html: str) -> None:
    """Save HTML to a file.

    Args:
        path: Path to write HTML file.
        html: HTML content to write.
    """
    with open(path, "w", encoding="utf-8") as write_file:
        write_file.write(html)


def save_svg(path: str, svg: str) -> None:
    """Save SVG to a file.

    Args:
        path: Path to write SVG file.
        svg: SVG content to write.
    """
    with open(path, "w", encoding="utf-8") as write_file:
        write_file.write(svg)
