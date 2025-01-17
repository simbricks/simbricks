from typer import Typer, Option
from typing import Annotated
from simbricks.client.provider import client_provider
from ..utils import async_cli, print_table_generic


app = Typer(help="Managing SimBricks resource groups used by runners.")


@app.command()
@async_cli()
async def create(label: str, available_cores: int, available_memory: int):
    """Create a resource group describing a runners available resources."""
    rg = await client_provider.resource_group_client.create_rg(
        label=label, available_cores=available_cores, available_memory=available_memory
    )
    print_table_generic(
        "Resource Group", [rg], "id", "label", "namespace_id", "available_cores", "available_memory", "cores_left", "memory_left"
    )


@app.command()
@async_cli()
async def update(
    rg_id: int,
    label: Annotated[str | None, Option("--label", "-l", help="Update the label.")] = None,
    available_cores: Annotated[int | None, Option("--ac", help="Update the available cores.")] = None,
    available_memory: Annotated[int | None, Option("--am", help="Update the available memory.")] = None,
    cores_left: Annotated[int | None, Option("--cl", help="Update the cores left.")] = None,
    memory_left: Annotated[int | None, Option("--ml", help="Update the memory left.")] = None,
):
    """Create a resource group describing a runners available resources."""
    rg = await client_provider.resource_group_client.update_rg(
        rg_id=rg_id,
        label=label,
        available_cores=available_cores,
        available_memory=available_memory,
        cores_left=cores_left,
        memory_left=memory_left,
    )
    print_table_generic(
        "Resource Group", [rg], "id", "label", "namespace_id", "available_cores", "available_memory", "cores_left", "memory_left"
    )


@app.command()
@async_cli()
async def ls_rg(rg_id: int):
    """List a resource group."""
    rg = await client_provider.resource_group_client.get_rg(rg_id=rg_id)
    print_table_generic(
        "Resource Group", [rg], "id", "label", "namespace_id", "available_cores", "available_memory", "cores_left", "memory_left"
    )


@app.command()
@async_cli()
async def ls():
    """List available resource groups."""
    rgs = await client_provider.resource_group_client.filter_get_rg()
    print_table_generic(
        "Resource Group", rgs, "id", "label", "namespace_id", "available_cores", "available_memory", "cores_left", "memory_left"
    )
