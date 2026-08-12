# MIT License
#
# Copyright (c) 2026 SimBricks
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Full-screen pager for cursor-paginated list endpoints."""

import sys
import typing

import readchar
from rich.console import Console, Group
from rich.live import Live
from rich.markup import escape
from rich.text import Text

from .utils import build_table

_NEXT_KEYS = frozenset(
    {
        readchar.key.RIGHT,
        readchar.key.DOWN,
        readchar.key.PAGE_DOWN,
        readchar.key.ENTER,
        "n",
        "l",
        " ",
    }
)
_PREV_KEYS = frozenset({readchar.key.LEFT, readchar.key.UP, readchar.key.PAGE_UP, "p", "h", "b"})
_FIRST_KEYS = frozenset({readchar.key.HOME, "g"})
_RELOAD_KEYS = frozenset({"r"})
# Ctrl+C is absent on purpose: readchar raises KeyboardInterrupt for it rather
# than returning it, which unwinds through Live and restores the terminal.
_QUIT_KEYS = frozenset({readchar.key.ESC, readchar.key.CTRL_D, "q", "Q"})

_HINTS = "[dim]←/→ page · g first · r reload · q quit[/dim]"

FetchPage = typing.Callable[[str | None], typing.Awaitable[tuple[list[typing.Any], str | None]]]


def interactive_supported() -> bool:
    """Whether a full-screen, keyboard-driven pager can be used here.

    False when either end of the terminal is redirected, which is the case
    whenever output is piped to a file or another command.
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


class _Page(typing.NamedTuple):
    rows: list[typing.Any]
    cursor: str | None  # cursor that produced this page, None for the first
    next_cursor: str | None  # cursor for the page after it, None when exhausted


class TablePager:
    """Full-screen pager over a cursor-paginated list endpoint.

    Pages that have been fetched are kept, so going backwards is instant and
    never depends on the server's ``cursorPrev`` behaviour. Only moving forward
    past the last cached page issues a request.
    """

    def __init__(
        self,
        title: str,
        columns: tuple[str, ...],
        first_page: tuple[list[typing.Any], str | None],
        fetch_page: FetchPage,
        console: Console | None = None,
    ) -> None:
        rows, next_cursor = first_page
        self._title = title
        self._columns = columns
        self._fetch_page = fetch_page
        self._console = console or Console()
        self._pages: list[_Page] = [_Page(rows=rows, cursor=None, next_cursor=next_cursor)]
        self._index = 0

    def _has_next(self) -> bool:
        return (
            self._index + 1 < len(self._pages) or self._pages[self._index].next_cursor is not None
        )

    def _render(self, status: str | None = None) -> Group:
        page = self._pages[self._index]
        last = "" if self._has_next() else "  [dim](last page)[/dim]"
        header = Text.from_markup(
            f"[bold]{escape(self._title)}[/bold]  [cyan]page {self._index + 1}[/cyan]"
            f"  [dim]{len(page.rows)} rows[/dim]{last}"
        )
        footer = Text.from_markup(_HINTS if status is None else status)
        # Header and hints go above the table so they stay visible on a
        # terminal too short for the whole page, where the table gets cropped.
        return Group(header, footer, "", build_table(None, page.rows, *self._columns))

    async def _load(self, cursor: str | None) -> _Page:
        rows, next_cursor = await self._fetch_page(cursor)
        if next_cursor is not None and (next_cursor == cursor or not rows):
            # A cursor that would not make progress, treat it as the end rather
            # than letting the user walk in circles.
            next_cursor = None
        return _Page(rows=rows, cursor=cursor, next_cursor=next_cursor)

    async def _go_next(self) -> None:
        if self._index + 1 < len(self._pages):
            self._index += 1
            return

        cursor = self._pages[self._index].next_cursor
        if cursor is None:
            return

        page = await self._load(cursor)
        if not page.rows:
            # Empty tail page, remember there is nothing more and stay put.
            self._pages[self._index] = self._pages[self._index]._replace(next_cursor=None)
            return

        self._pages.append(page)
        self._index += 1

    async def _reload(self) -> None:
        # Fetch before mutating so a failed reload leaves the cache intact. The
        # pages after this one are dropped, the list underneath may have moved.
        page = await self._load(self._pages[self._index].cursor)
        del self._pages[self._index :]
        self._pages.append(page)

    async def run(self) -> None:
        # auto_refresh=False keeps rich from running a background refresh
        # thread, every frame below is drawn explicitly instead.
        with Live(self._render(), console=self._console, screen=True, auto_refresh=False) as live:
            while True:
                key = readchar.readkey()

                if key in _QUIT_KEYS:
                    break

                if key in _PREV_KEYS:
                    self._index = max(self._index - 1, 0)
                elif key in _FIRST_KEYS:
                    self._index = 0
                elif key in _NEXT_KEYS or key in _RELOAD_KEYS:
                    live.update(self._render(status="[dim]loading ...[/dim]"), refresh=True)
                    status = None
                    try:
                        if key in _RELOAD_KEYS:
                            await self._reload()
                        else:
                            await self._go_next()
                    except Exception as exc:  # keep the pager alive on a blip
                        status = (
                            f"[red]{escape(type(exc).__name__)}: {escape(str(exc))}[/red]"
                            "  [dim](r to retry)[/dim]"
                        )
                    live.update(self._render(status=status), refresh=True)
                    continue
                else:
                    continue  # unknown key

                live.update(self._render(), refresh=True)

        # screen=True restores the previous screen contents on exit, so echo the
        # page the user was looking at into the real scrollback. Copying a run
        # id out of it is the whole point of the command.
        self._console.print(build_table(self._title, self._pages[self._index].rows, *self._columns))
