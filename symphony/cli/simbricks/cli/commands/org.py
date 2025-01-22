from typer import Typer, Option
from typing import Annotated
from simbricks.client.provider import client_provider
from ..utils import async_cli, print_table_generic


app = Typer(help="Managing SimBricks organizations.")

organization = ''

@app.callback()
@async_cli()
async def amain(
    org: Annotated[str, Option(help="Organization to operate in.")] = "SimBricks",
):
    global organization
    organization = org

@app.command()
@async_cli()
async def members():
    """List organization members."""
    members = await client_provider.org_client.get_members(organization)

    print_table_generic(
        "Members", members, "username", "first_name", "last_name"
    )


@app.command()
@async_cli()
async def invite(email: str, first_name: str, last_name: str):
    """Invite a new user."""
    await client_provider.org_client.invite_member(organization, email, first_name, last_name)


@app.command()
@async_cli()
async def guest(email: str, first_name: str, last_name: str):
    """Invite a new user."""
    url = await client_provider.org_client.create_guest(organization, email, first_name, last_name)
    print("Guest login link: {url}")
