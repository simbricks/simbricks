from typer import Typer
from simbricks.client.provider import client_provider
from ..utils import async_cli, print_table_generic


app = Typer(help="Managing SimBricks resource groups used by runners.")


@app.command()
@async_cli()
async def create_rg(label: str, available_cores: int, available_memory: int):
    """Create a resource group describing a runners available resources."""
    rg = await client_provider.resource_group_client.create_rg(
        label=label, available_cores=available_cores, available_memory=available_memory
    )
    print_table_generic(
        "Resource Group", [rg], "id", "label", "available_cores", "available_memory", "cores_left", "memory_left"
    )


@app.command()
@async_cli()
async def ls_rg(rg_id: int):
    """List a resource group."""
    rg = await client_provider.resource_group_client.get_rg(rg_id=rg_id)
    print_table_generic(
        "Resource Group", [rg], "id", "label", "available_cores", "available_memory", "cores_left", "memory_left"
    )


@app.command()
@async_cli()
async def ls():
    """List available resource groups."""
    rgs = await client_provider.resource_group_client.filter_get_rg()
    print_table_generic(
        "Resource Group", rgs, "id", "label", "available_cores", "available_memory", "cores_left", "memory_left"
    )
