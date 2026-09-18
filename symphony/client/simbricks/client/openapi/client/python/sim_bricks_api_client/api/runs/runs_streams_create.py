from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...models.stream import Stream
from ...models.stream_create import StreamCreate
from ...types import UNSET, Response, Unset


def _get_kwargs(
    ns_path: str,
    run_id: str,
    *,
    body: StreamCreate | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/ns/{ns_path}/-/runs/{run_id}/streams".format(
            ns_path=quote(str(ns_path), safe=""),
            run_id=quote(str(run_id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InlineObject | Stream | None:
    if response.status_code == 201:
        response_201 = Stream.from_dict(response.json())

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

    if response.status_code == 409:
        response_409 = InlineObject.from_dict(response.json())

        return response_409

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = InlineObject.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | InlineObject | Stream]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    ns_path: str,
    run_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: StreamCreate | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | Stream]:
    """Open a stream from the client to one fragment of a run

     Creates a stream and returns the client's websocket ticket URL. The runner
    executing the fragment receives its own ticket in a StreamCreated event.

    Args:
        ns_path (str):
        run_id (str):
        body (StreamCreate | Unset): Request body for a client opening a stream to one fragment of
            a run.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | Stream]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        run_id=run_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    run_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: StreamCreate | Unset = UNSET,
) -> HTTPValidationError | InlineObject | Stream | None:
    """Open a stream from the client to one fragment of a run

     Creates a stream and returns the client's websocket ticket URL. The runner
    executing the fragment receives its own ticket in a StreamCreated event.

    Args:
        ns_path (str):
        run_id (str):
        body (StreamCreate | Unset): Request body for a client opening a stream to one fragment of
            a run.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | Stream
    """

    return sync_detailed(
        ns_path=ns_path,
        run_id=run_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    run_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: StreamCreate | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | Stream]:
    """Open a stream from the client to one fragment of a run

     Creates a stream and returns the client's websocket ticket URL. The runner
    executing the fragment receives its own ticket in a StreamCreated event.

    Args:
        ns_path (str):
        run_id (str):
        body (StreamCreate | Unset): Request body for a client opening a stream to one fragment of
            a run.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | Stream]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        run_id=run_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    run_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: StreamCreate | Unset = UNSET,
) -> HTTPValidationError | InlineObject | Stream | None:
    """Open a stream from the client to one fragment of a run

     Creates a stream and returns the client's websocket ticket URL. The runner
    executing the fragment receives its own ticket in a StreamCreated event.

    Args:
        ns_path (str):
        run_id (str):
        body (StreamCreate | Unset): Request body for a client opening a stream to one fragment of
            a run.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | Stream
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            run_id=run_id,
            client=client,
            body=body,
        )
    ).parsed
