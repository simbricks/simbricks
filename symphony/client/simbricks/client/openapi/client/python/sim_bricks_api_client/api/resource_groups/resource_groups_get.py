from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...models.resource_group import ResourceGroup
from ...types import Response


def _get_kwargs(
    ns_path: str,
    rg_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/ns/{ns_path}/-/resource-group/{rg_id}".format(
            ns_path=quote(str(ns_path), safe=""),
            rg_id=quote(str(rg_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InlineObject | ResourceGroup | None:
    if response.status_code == 200:
        response_200 = ResourceGroup.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = InlineObject.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = InlineObject.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = InlineObject.from_dict(response.json())

        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | InlineObject | ResourceGroup]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    ns_path: str,
    rg_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | InlineObject | ResourceGroup]:
    """Retrieve individual resource group

    Args:
        ns_path (str):
        rg_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | ResourceGroup]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        rg_id=rg_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    rg_id: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | InlineObject | ResourceGroup | None:
    """Retrieve individual resource group

    Args:
        ns_path (str):
        rg_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | ResourceGroup
    """

    return sync_detailed(
        ns_path=ns_path,
        rg_id=rg_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    rg_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | InlineObject | ResourceGroup]:
    """Retrieve individual resource group

    Args:
        ns_path (str):
        rg_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | ResourceGroup]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        rg_id=rg_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    rg_id: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | InlineObject | ResourceGroup | None:
    """Retrieve individual resource group

    Args:
        ns_path (str):
        rg_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | ResourceGroup
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            rg_id=rg_id,
            client=client,
        )
    ).parsed
