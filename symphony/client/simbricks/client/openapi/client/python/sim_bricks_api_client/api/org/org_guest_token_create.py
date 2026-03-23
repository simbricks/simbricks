from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...models.org_guest_cred import OrgGuestCred
from ...types import UNSET, Response, Unset


def _get_kwargs(
    org: str,
    *,
    body: OrgGuestCred | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/org/{org}/guest-token".format(
            org=quote(str(org), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | HTTPValidationError | InlineObject | None:
    if response.status_code == 200:
        response_200 = response.json()
        return response_200

    if response.status_code == 401:
        response_401 = InlineObject.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | HTTPValidationError | InlineObject]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    org: str,
    *,
    client: AuthenticatedClient,
    body: OrgGuestCred | Unset = UNSET,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Guest Token

     Invite a user to the organization.

    Args:
        org (str):
        body (OrgGuestCred | Unset): OrgGuestCred

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        org=org,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    org: str,
    *,
    client: AuthenticatedClient,
    body: OrgGuestCred | Unset = UNSET,
) -> Any | HTTPValidationError | InlineObject | None:
    """Guest Token

     Invite a user to the organization.

    Args:
        org (str):
        body (OrgGuestCred | Unset): OrgGuestCred

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return sync_detailed(
        org=org,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    org: str,
    *,
    client: AuthenticatedClient,
    body: OrgGuestCred | Unset = UNSET,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Guest Token

     Invite a user to the organization.

    Args:
        org (str):
        body (OrgGuestCred | Unset): OrgGuestCred

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        org=org,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    org: str,
    *,
    client: AuthenticatedClient,
    body: OrgGuestCred | Unset = UNSET,
) -> Any | HTTPValidationError | InlineObject | None:
    """Guest Token

     Invite a user to the organization.

    Args:
        org (str):
        body (OrgGuestCred | Unset): OrgGuestCred

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return (
        await asyncio_detailed(
            org=org,
            client=client,
            body=body,
        )
    ).parsed
