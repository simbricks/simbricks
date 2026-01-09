from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...models.runners_list_200_response import RunnersList200Response
from ...types import UNSET, Response, Unset


def _get_kwargs(
    ns_path: str,
    *,
    cursor_next: None | str | Unset = UNSET,
    cursor_prev: None | str | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    deleted: bool | None | Unset = UNSET,
    resource_group: None | str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_cursor_next: None | str | Unset
    if isinstance(cursor_next, Unset):
        json_cursor_next = UNSET
    else:
        json_cursor_next = cursor_next
    params["cursorNext"] = json_cursor_next

    json_cursor_prev: None | str | Unset
    if isinstance(cursor_prev, Unset):
        json_cursor_prev = UNSET
    else:
        json_cursor_prev = cursor_prev
    params["cursorPrev"] = json_cursor_prev

    json_limit: int | None | Unset
    if isinstance(limit, Unset):
        json_limit = UNSET
    else:
        json_limit = limit
    params["limit"] = json_limit

    json_deleted: bool | None | Unset
    if isinstance(deleted, Unset):
        json_deleted = UNSET
    else:
        json_deleted = deleted
    params["deleted"] = json_deleted

    json_resource_group: None | str | Unset
    if isinstance(resource_group, Unset):
        json_resource_group = UNSET
    else:
        json_resource_group = resource_group
    params["resource_group"] = json_resource_group

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/ns/{ns_path}/-/runners".format(
            ns_path=quote(str(ns_path), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InlineObject | RunnersList200Response | None:
    if response.status_code == 200:
        response_200 = RunnersList200Response.from_dict(response.json())

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
) -> Response[HTTPValidationError | InlineObject | RunnersList200Response]:
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
    cursor_next: None | str | Unset = UNSET,
    cursor_prev: None | str | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    deleted: bool | None | Unset = UNSET,
    resource_group: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | RunnersList200Response]:
    """Retrieve runners

    Args:
        ns_path (str):
        cursor_next (None | str | Unset): Cursor for pagination next page
        cursor_prev (None | str | Unset): Cursor for pagination previous page
        limit (int | None | Unset): Rough number of items to return
        deleted (bool | None | Unset):
        resource_group (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | RunnersList200Response]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        cursor_next=cursor_next,
        cursor_prev=cursor_prev,
        limit=limit,
        deleted=deleted,
        resource_group=resource_group,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    cursor_next: None | str | Unset = UNSET,
    cursor_prev: None | str | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    deleted: bool | None | Unset = UNSET,
    resource_group: None | str | Unset = UNSET,
) -> HTTPValidationError | InlineObject | RunnersList200Response | None:
    """Retrieve runners

    Args:
        ns_path (str):
        cursor_next (None | str | Unset): Cursor for pagination next page
        cursor_prev (None | str | Unset): Cursor for pagination previous page
        limit (int | None | Unset): Rough number of items to return
        deleted (bool | None | Unset):
        resource_group (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | RunnersList200Response
    """

    return sync_detailed(
        ns_path=ns_path,
        client=client,
        cursor_next=cursor_next,
        cursor_prev=cursor_prev,
        limit=limit,
        deleted=deleted,
        resource_group=resource_group,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    cursor_next: None | str | Unset = UNSET,
    cursor_prev: None | str | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    deleted: bool | None | Unset = UNSET,
    resource_group: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | InlineObject | RunnersList200Response]:
    """Retrieve runners

    Args:
        ns_path (str):
        cursor_next (None | str | Unset): Cursor for pagination next page
        cursor_prev (None | str | Unset): Cursor for pagination previous page
        limit (int | None | Unset): Rough number of items to return
        deleted (bool | None | Unset):
        resource_group (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InlineObject | RunnersList200Response]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        cursor_next=cursor_next,
        cursor_prev=cursor_prev,
        limit=limit,
        deleted=deleted,
        resource_group=resource_group,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    *,
    client: AuthenticatedClient,
    cursor_next: None | str | Unset = UNSET,
    cursor_prev: None | str | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    deleted: bool | None | Unset = UNSET,
    resource_group: None | str | Unset = UNSET,
) -> HTTPValidationError | InlineObject | RunnersList200Response | None:
    """Retrieve runners

    Args:
        ns_path (str):
        cursor_next (None | str | Unset): Cursor for pagination next page
        cursor_prev (None | str | Unset): Cursor for pagination previous page
        limit (int | None | Unset): Rough number of items to return
        deleted (bool | None | Unset):
        resource_group (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InlineObject | RunnersList200Response
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            client=client,
            cursor_next=cursor_next,
            cursor_prev=cursor_prev,
            limit=limit,
            deleted=deleted,
            resource_group=resource_group,
        )
    ).parsed
