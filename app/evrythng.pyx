from __future__ import absolute_import, division, print_function, unicode_literals

import enum
import sys
import uuid
from typing import Tuple, Any, List, Union
from urllib import parse

import requests
from httpx import URL, AsyncClient, QueryParams, PoolLimits, Headers

try:
    import ujson as json
except ModuleNotFoundError as err:
    sys.stderr(str(err))
    sys.stderr('\n')
    import json

EVT_HOST = 'https://api.evrythng.com'


class Resources(enum.Enum):
    ACTION = 'actions'
    THNG = 'thngs'
    PRODUCT = 'products'
    PROJECT = 'projects'
    PLACE = 'places'
    APPLICATION = 'applications'


cpdef int new_timestamp():
    from datetime import datetime
    return round(datetime.timestamp(datetime.now()) * 1000)

cpdef new_resource_id():
    return uuid.uuid4().hex


class ResourceDocument:
    # id: str
    # name: str
    # timestamp: int
    # created_at: int
    # customFields: dict
    # tags: List[str]
    # links: dict
    # description: str

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

def flatten_dict(obj) -> List[Tuple[Union[type(None), str], Any]]:
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
                             default_redirection_url: str) -> dict:
    redirection_document = {
        "defaultRedirectUrl": default_redirection_url,
        "evrythngId": evrythng_id,
        "type": resource_type
    }
    res = await client.post('https://tn.gg/redirections', json=redirection_document)
    if 200 <= res.status_code < 300:
        short_url = res.headers['content-disposition'].split(';')[1].strip()
        short_id = parse.urlparse(short_url).path[1:]
        return dict(shortUrl=short_url, shortId=short_id)
    else:
        raise Exception(res.content)

cpdef items_to_evt_filter(filter_conditions):
    if filter_conditions:
        k, v = filter_conditions.pop()
        q = items_to_evt_filter(filter_conditions)
        return f'{k}={v}' if q is None else f'{q}&{k}={v}'
    else:
        return None

cdef dict gen_idx(dict p):
    return {p[i]: i for i in range(len(p))[::-1]}

cdef path_key(p):
    idx = gen_idx(p)
    if '/' in idx:
        k = p[:idx['/']]
        v, path_dict = path_value(p[idx['/'] + 1:])
        path_dict[k] = v
        return path_dict
    else:
        raise Exception('Invalid path')

cdef path_value(p):
    idx = gen_idx(p)
    if '/' in idx:
        v = p[:idx['/']]
        return v, path_key(p[idx['/'] + 1:])
    else:
        return p, {}

cpdef path_to_dict(path):
    if path[0] == '/':
        path = path[1:]

    if path[-1] == '/':
        path = path[:-1]

    return path_key(path)

async def download_resources(client: AsyncClient, path: str, project_id: str = None, **filter_conditions):
    # number_of_thngs: int,
    per_page = 100
    # remaining = min(number_of_thngs, per_page)
    remaining = per_page
    link_header = {}
    query_params = dict(perPage=per_page)

    if filter_conditions:
        query_params['filter'] = f'{parse.quote(items_to_evt_filter(list(filter_conditions.items())))}'
    if project_id:
        query_params['project'] = project_id

    query = QueryParams(query_params)

    while remaining > 0:
        query.update({'perPage': min(per_page, remaining)})
        url = parse.urljoin(EVT_HOST, path) + '?' + str(query)

        res = await client.get(url)
        if 200 <= res.status_code < 300:
            for resource in res.json():
                if remaining == 0:
                    break
                yield resource
                remaining -= 1
        elif 500 <= res.status_code:
            raise Exception(res)
        if 'link' not in link_header:
            break
        link_header = requests.utils.parse_header_links(parse.unquote(res.headers['link']))
        if len(link_header) == 0:
            raise Exception('Link header is empty')
        url = URL(link_header.pop()['url'])
        query = QueryParams(url.query)


class APIKeyType(enum.Enum):
    OPERATOR = 'operator'
    APP = 'app'
    TRUSTED_APP = 'trusted_app'


class APIKey:

    def __init__(self, str api_key, str key_id, str key_type, str project_id, str  account_id):
        self.api_key = api_key
        self.key_id = key_id
        self.key_type = APIKeyType(key_type)
        self.project_id = project_id
        self.account_id = account_id

    @staticmethod
    async def api_key_information(client: AsyncClient, project_name):
        # headers = dict(Authorization=api_key, ContentType='application/json')
        # async with httpx.AsyncClient(headers=headers) as client:
        # print(await APIKey.__get_access_id(client, EVT_HOST))
        # print(await APIKey.get_account_info(client, EVT_HOST))
        #

        # await APIKey.__get_app_api_key_subtype(client, EVT_HOST)
        # {'account': 'UXPNn8b3rxRaUyxKB9stahKf', 'actor': {'type': 'operator', 'id': 'UDsNnsxmeFFwSqxdTWBSPwcs'}}
        # {'account': 'UXPNn8b3rxRaUyxKB9stahKf', 'project': 'UskCRKCXfrDkUHcNEDCNAxqn', 'actor': {'type': 'app', 'id': 'UsFCapfgYKxa8mx3APBRnfcc'}}
        access = await APIKey.__get_access_id(client)
        if APIKeyType(access['actor']['type']) is APIKeyType.OPERATOR:
            projects = await lookup(client, Resources.PROJECT.value, dict(name=project_name))
            if not projects:
                raise Exception(f"Hospital {project_name} not found")
            if len(projects) != 1:
                raise Exception(f"Ambiguous hospital name  {project_name}. {len(projects)} match that name")
            return APIKey(
                api_key=client.headers['Authorization'],
                key_id=access['actor']['id'],
                key_type=access['actor']['type'],
                project_id=projects[0]['id'],
                account_id=access['account']
            )
        elif APIKeyType(access['actor']['type']) is APIKeyType.APP:
            return APIKey(
                api_key=client.headers['Authorization'],
                key_id=access['actor']['id'],
                key_type=await APIKey.__get_app_api_key_subtype(client),
                project_id=access['project'],
                account_id=access['account']
            )
        else:
            raise Exception(f'An error occurred while trying to lookup api key')

    @staticmethod
    async def __get_app_api_key_subtype(client: AsyncClient) -> str:
        res = await client.get(parse.urljoin(EVT_HOST, "/thngs") + "?perPage=1")
        data = res.json()
        if 200 <= res.status_code < 300:
            return 'trusted_app'
        elif res.status_code == 403:
            return 'app'
        else:
            raise Exception(f'Unknown api key')

    @staticmethod
    async def __get_access_id(client: AsyncClient) -> dict:
        res = await client.get(parse.urljoin(EVT_HOST, "access"))
        data = res.json()
        if 200 <= res.status_code < 300:
            return data
        else:
            return None

    @staticmethod
    async def __get_account_info(client: AsyncClient) -> dict:
        res = await client.get(parse.urljoin(EVT_HOST, "accounts"))
        data = res.json()
        if 200 <= res.status_code < 300:
            return data
        else:
            return None
