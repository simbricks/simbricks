from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...types import Response


def _get_kwargs(
    ns_path: str,
    runner_id: str,
    event_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/ns/{ns_path}/-/runners/{runner_id}/events-to-runner/{event_id}".format(
            ns_path=quote(str(ns_path), safe=""),
            runner_id=quote(str(runner_id), safe=""),
            event_id=quote(str(event_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | HTTPValidationError | InlineObject | None:
    if response.status_code == 200:
        response_200 = response.json()
        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

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
) -> Response[Any | HTTPValidationError | InlineObject]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    ns_path: str,
    runner_id: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Delete event from backend to runner

     Note that this operation is cumulative. Deleting an event id, will also mark earlier events in the
    queue as deleted.

    Args:
        ns_path (str):
        runner_id (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        runner_id=runner_id,
        event_id=event_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    runner_id: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Any | HTTPValidationError | InlineObject | None:
    """Delete event from backend to runner

     Note that this operation is cumulative. Deleting an event id, will also mark earlier events in the
    queue as deleted.

    Args:
        ns_path (str):
        runner_id (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return sync_detailed(
        ns_path=ns_path,
        runner_id=runner_id,
        event_id=event_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    runner_id: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Delete event from backend to runner

     Note that this operation is cumulative. Deleting an event id, will also mark earlier events in the
    queue as deleted.

    Args:
        ns_path (str):
        runner_id (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        runner_id=runner_id,
        event_id=event_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    runner_id: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Any | HTTPValidationError | InlineObject | None:
    """Delete event from backend to runner

     Note that this operation is cumulative. Deleting an event id, will also mark earlier events in the
    queue as deleted.

    Args:
        ns_path (str):
        runner_id (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            runner_id=runner_id,
            event_id=event_id,
            client=client,
        )
    ).parsed
