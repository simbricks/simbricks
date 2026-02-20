from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...models.runner import Runner
from ...types import UNSET, Response, Unset


def _get_kwargs(
    ns_path: str,
    *,
    body: Runner | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/ns/{ns_path}/-/runners".format(
            ns_path=quote(str(ns_path), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InlineObject | Runner | None:
    if response.status_code == 200:
        response_200 = Runner.from_dict(response.json())

        return response_200

    if response.status_code == 201:
        response_201 = Runner.from_dict(response.json())

        return response_201

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
) -> Response[HTTPValidationError | InlineObject | Runner]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    body: Runner | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | Runner]:
    """Create a new runner

    Args:
        ns_path (str):
        body (Runner | Unset): Runner

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | Runner]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    body: Runner | Unset = UNSET,
) -> HTTPValidationError | InlineObject | Runner | None:
    """Create a new runner

    Args:
        ns_path (str):
        body (Runner | Unset): Runner

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | Runner
    """

    return sync_detailed(
        ns_path=ns_path,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    body: Runner | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | Runner]:
    """Create a new runner

    Args:
        ns_path (str):
        body (Runner | Unset): Runner

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | Runner]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    body: Runner | Unset = UNSET,
) -> HTTPValidationError | InlineObject | Runner | None:
    """Create a new runner

    Args:
        ns_path (str):
        body (Runner | Unset): Runner

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | Runner
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            client=client,
            body=body,
        )
    ).parsed
