from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.body_runs_fragments_output_artifact_set_ns_ns_path_runs_run_id_fragments_frag_id_output_artifacts_put import (
    BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut,
)
from ...models.http_validation_error import HTTPValidationError
from ...models.inline_object import InlineObject
from ...types import UNSET, Response, Unset


def _get_kwargs(
    ns_path: str,
    run_id: str,
    frag_id: str,
    *,
    body: BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/ns/{ns_path}/-/runs/{run_id}/fragments/{frag_id}/output-artifacts".format(
            ns_path=quote(str(ns_path), safe=""),
            run_id=quote(str(run_id), safe=""),
            frag_id=quote(str(frag_id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["data"] = body.to_dict()

    headers["Content-Type"] = "application/x-www-form-urlencoded"

    _kwargs["headers"] = headers
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
    run_id: str,
    frag_id: str,
    *,
    client: AuthenticatedClient,
    body: BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut | Unset = UNSET,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Get Run Output

    Args:
        ns_path (str):
        run_id (str):
        frag_id (str):
        body (BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut
            | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        run_id=run_id,
        frag_id=frag_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    ns_path: str,
    run_id: str,
    frag_id: str,
    *,
    client: AuthenticatedClient,
    body: BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut | Unset = UNSET,
) -> Any | HTTPValidationError | InlineObject | None:
    """Get Run Output

    Args:
        ns_path (str):
        run_id (str):
        frag_id (str):
        body (BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut
            | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return sync_detailed(
        ns_path=ns_path,
        run_id=run_id,
        frag_id=frag_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    ns_path: str,
    run_id: str,
    frag_id: str,
    *,
    client: AuthenticatedClient,
    body: BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut | Unset = UNSET,
) -> Response[Any | HTTPValidationError | InlineObject]:
    """Get Run Output

    Args:
        ns_path (str):
        run_id (str):
        frag_id (str):
        body (BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut
            | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | InlineObject]
    """

    kwargs = _get_kwargs(
        ns_path=ns_path,
        run_id=run_id,
        frag_id=frag_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    ns_path: str,
    run_id: str,
    frag_id: str,
    *,
    client: AuthenticatedClient,
    body: BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut | Unset = UNSET,
) -> Any | HTTPValidationError | InlineObject | None:
    """Get Run Output

    Args:
        ns_path (str):
        run_id (str):
        frag_id (str):
        body (BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut
            | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | InlineObject
    """

    return (
        await asyncio_detailed(
            ns_path=ns_path,
            run_id=run_id,
            frag_id=frag_id,
            client=client,
            body=body,
        )
    ).parsed
