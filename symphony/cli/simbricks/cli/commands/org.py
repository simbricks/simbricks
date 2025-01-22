from typer import Typer, Option
from typing import Annotated
from simbricks.client.provider import client_provider
from simbricks.client.settings import client_settings
from ..utils import async_cli, print_table_generic


app = Typer(help="Managing SimBricks organizations.")

organization = ""


@app.callback()
@async_cli()
async def amain(
    org: Annotated[str, Option(help="Organization to operate in.")] = client_settings().organization,
):
    global organization
    organization = org


@app.command()
@async_cli()
async def members():
    """List organization members."""
    members = await client_provider.org_client.get_members(organization)

    print_table_generic("Members", members, "username", "first_name", "last_name")


@app.command()
@async_cli()
async def invite(email: str, first_name: str, last_name: str):
    """Invite a new user."""
    await client_provider.org_client.invite_member(organization, email, first_name, last_name)


@app.command()
@async_cli()
async def guest(
    email: str,
    first_name: str,
    last_name: str,
    generate_token: Annotated[str, Option(help='File name to store an auth token into, if specified.', show_default=False)] = ''
    ):
    """Create a new guest user."""
    await client_provider.org_client.create_guest(organization, email, first_name, last_name)
    if generate_token:
        tok = await client_provider.org_client.guest_token(organization, email)
        tok.store_token(generate_token)

@app.command()
@async_cli()
async def guest_token(email: str, filename: str):
    """Generate token for guest account."""
    tok = await client_provider.org_client.guest_token(organization, email)
    tok.store_token(filename)

@app.command()
@async_cli()
async def guest_link(email: str, filename: str):
    """Generate magic login link for guest account."""
    link = await client_provider.org_client.guest_magic_link(organization, email)
    print(link)