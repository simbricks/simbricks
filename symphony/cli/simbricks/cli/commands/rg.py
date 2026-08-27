from typing import Annotated

from typer import Option, Typer

from simbricks.client.opus import base as opus_base

from ..pager import PAGE_SIZE, PEEK_COUNT, paged_ls
from ..settings import rg_client
from ..utils import async_cli, print_table_generic

app = Typer(help="Managing SimBricks resource groups used by runners.")

_RESOURCE_GROUP_COLUMNS = (
    "id",
    "label",
    "namespace_id",
    "available_cores",
    "available_memory",
    "cores_left",
    "memory_left",
)


@app.command()
@async_cli()
async def create(label: str, available_cores: int, available_memory: int):
    """Create a resource group describing a runners available resources."""
    rgc = await rg_client()
    rg = await rgc.create_rg(
        label=label, available_cores=available_cores, available_memory=available_memory
    )
    print_table_generic("Resource Group", [rg], *_RESOURCE_GROUP_COLUMNS)


@app.command()
@async_cli()
async def update(
    rg_id: str,
    label: Annotated[str | None, Option("--label", "-l", help="Update the label.")] = None,
    available_cores: Annotated[
        int | None, Option("--ac", help="Update the available cores.")
    ] = None,
    available_memory: Annotated[
        int | None, Option("--am", help="Update the available memory.")
    ] = None,
    cores_left: Annotated[int | None, Option("--cl", help="Update the cores left.")] = None,
    memory_left: Annotated[int | None, Option("--ml", help="Update the memory left.")] = None,
):
    """Create a resource group describing a runners available resources."""
    rgc = await rg_client()
    rg = await rgc.update_rg(
        rg_id=rg_id,
        label=label,
        available_cores=available_cores,
        available_memory=available_memory,
        cores_left=cores_left,
        memory_left=memory_left,
    )
    print_table_generic("Resource Group", [rg], *_RESOURCE_GROUP_COLUMNS)


@app.command()
@async_cli()
async def show(rg_id: str):
    """List a resource group."""
    rgc = await rg_client()
    rg = await rgc.get_rg(rg_id=rg_id)
    print_table_generic("Resource Group", [rg], *_RESOURCE_GROUP_COLUMNS)


@app.command()
@async_cli()
async def ls(
    limit: Annotated[
        int, Option("--limit", "-n", help="Number of resource groups per page.")
    ] = PAGE_SIZE,
    fetch_all: Annotated[
        bool,
        Option(
            "--all",
            "-a",
            help="Retrieve every resource group at once instead of paging through them.",
        ),
    ] = False,
):
    """List available resource groups.

    Pages interactively when there is more than one page and the output is a
    terminal. Left and right change page, g jumps back to the first page, r
    reloads the current one and q quits.
    """
    rgc = await rg_client()
    page_limit = None if fetch_all else limit
    await paged_ls(
        "Resource Group",
        _RESOURCE_GROUP_COLUMNS,
        lambda cursor: opus_base.get_resource_groups_page(
            rgc, cursor_next=cursor, limit=page_limit
        ),
    )


@app.command()
@async_cli()
async def peek(
    limit: Annotated[
        int, Option("--limit", "-n", help="Number of resource groups to peek.")
    ] = PEEK_COUNT,
):
    """Show the most recent resource groups, 5 by default."""
    rgc = await rg_client()
    rgs, _ = await opus_base.get_resource_groups_page(rgc, limit=limit)
    print_table_generic("Latest Resource Groups", rgs, *_RESOURCE_GROUP_COLUMNS)


@app.command()
@async_cli()
async def rm(rg_id: str):
    """Delete an individual runner."""
    rgc = await rg_client()
    await rgc.delete_rg(rg_id)
