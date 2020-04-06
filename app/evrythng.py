from __future__ import absolute_import, division, print_function, unicode_literals

import enum
import sys
import uuid
from typing import Tuple, Any, List, Union
from urllib import parse

from httpx import URL, AsyncClient

EVT_HOST = 'https://api.evrythng.com'


class Resources(enum.Enum):
    ACTION = 'actions'
    THNG = 'thngs'
    PRODUCT = 'products'
    PROJECT = 'projects'
    PLACE = 'places'
    APPLICATION = 'applications'


try:
    import ujson as json
except ModuleNotFoundError as err:
    print(err, file=sys.stderr)
    import json


def new_timestamp() -> int:
    from datetime import datetime
    return round(datetime.timestamp(datetime.now()) * 1000)


def new_resource_id() -> str:
    return uuid.uuid4().hex


class ResourceDocument:
    id: str
    name: str
    timestamp: int
    created_at: int
    customFields: dict
    tags: List[str]
    links: dict
    description: str

    def __init__(self,
                 resource_id: str = None,
                 name: str = None,
                 description: str = None,
                 timestamp: int = None,
                 tags: List[str] = None,
                 created_at: int = None,
                 identifiers: dict = None,
                 **custom_fields: dict):
        if name:
            self.name = name
        if description:
            self.description = description
        if identifiers:
            self.identifiers = identifiers
        if resource_id:
            self.id = resource_id
        if timestamp:
            self.timestamp = timestamp
        if not tags:
            self.tags = []
        else:
            self.tags = tags
        if created_at:
            self.createdAt = created_at

        self.customFields = {}
        if custom_fields:
            self.set_filtered_custom_fields(custom_fields)
        # self.links = dict()

    def set_filtered_custom_fields(self, custom_fields: dict):
        """
        This removes redundant entries, e.g. model_type doesn't have to be specified as custom fields as well
        :param custom_fields:
        :return: None
        """

        for k in frozenset(custom_fields.keys()) - frozenset(self.__dict__.keys()):
            self.customFields[k] = custom_fields[k]

    def _as_dict(self) -> dict:
        """
        This will return a copy of this object as dictionary, with internal fields and fields without values omitted
        :return: dict
        """
        return dict((k, self.__dict__[k]) for k in self.__dict__ if k[0] != '_' and self.__dict__[k] is not None)

    def dict(self) -> dict:
        return self._as_dict()


def dict_to_query(query: dict) -> str:
    return '&'.join(f'{k}={query[k]}' for k in query)


def flatten_dict(obj: dict) -> List[Tuple[Union[type(None), str], Any]]:
    out = []
    if type(obj) is dict:
        for k in obj:
            for ck, v in flatten_dict(obj[k]):
                if ck is None:
                    out.append((k, v))
                else:
                    out.append(('.'.join([k, ck]), v))
    else:
        out.append((None, obj))
    return out


def encode_query(query: dict) -> dict:
    return dict(filter=dict_to_query(dict(flatten_dict(query))))


async def new_resource(client: AsyncClient, resource: Union[Resources, str], project_scope: str,
                       resource_document: dict) -> dict:
    if type(resource) is Resources:
        resource_str = resource.value
    else:
        resource_str = resource
    res = await client.post(parse.urljoin(EVT_HOST, resource_str) + f'?project={project_scope}', json=resource_document)
    if 200 <= res.status_code < 300:
        return res.json()
    else:
        raise Exception(res.content)


async def new_property(client: AsyncClient, thng_id: str, project_scope: str,
                       property_name: str, property_value: Any) -> dict:
    res = await client.put(
        parse.urljoin(EVT_HOST, f'/thngs/{thng_id}/properties') + f'?project={project_scope}',
        json=[dict(key=property_name, value=property_value)])
    if 200 <= res.status_code < 300:
        return res.json()
    else:
        raise Exception(res.content)


async def update_resource(client: AsyncClient, resource: Union[Resources, str], resource_id: str,
                          resource_document: dict) -> dict:
    if type(resource) is Resources:
        resource_str = resource.value
    else:
        resource_str = resource

    res = await client.put(parse.urljoin(EVT_HOST, '/'.join([resource_str, resource_id])), json=resource_document)
    if 200 <= res.status_code < 300:
        return res.json()
    else:
        raise Exception(res.content)


def __compile_name_to_identifier():
    import re
    p = re.compile('(\w+)')

    def _fn(word):
        return '_'.join(p.findall(word)).lower()

    return _fn


name_to_identifier = __compile_name_to_identifier()


async def lookup(client: AsyncClient, path: str, search_query: dict) -> List[dict]:
    res = await client.get(URL(parse.urljoin(EVT_HOST, path), params=encode_query(search_query)))
    if 200 <= res.status_code < 300:
        return res.json()
    else:
        raise Exception(res.content)


async def create_redirection(client: AsyncClient, evrythng_id: str, resource_type: str,
                             default_redirection_url: str) -> Any:
    redirection_document = {
        "defaultRedirectUrl": default_redirection_url,
        "evrythngId": evrythng_id,
        "type": resource_type
    }
    res = await client.post('https://tn.gg/redirections', json=redirection_document)
    if 200 <= res.status_code < 300:
        return res.content
    else:
        raise Exception(res.content)
