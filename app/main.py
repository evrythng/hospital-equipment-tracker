from __future__ import absolute_import, division, print_function, unicode_literals
import pyximport;

pyximport.install(language_level=3)
import os
from typing import Optional
from urllib import parse

import httpx
import tagging

from starlette.responses import HTMLResponse, UJSONResponse as JSONResponse, FileResponse

from evrythng import Resources, ResourceDocument, new_resource, lookup, update_resource, EVT_HOST, create_redirection, \
    name_to_identifier, new_property, download_resources, APIKey

from fastapi import FastAPI, File, UploadFile, Path, Header, Body, Query
from starlette.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
import schemas

app = FastAPI()
HOSPITAL_HOST = 'https://covid.evrythng.io'


@app.post("/hospitals", status_code=HTTP_201_CREATED)
async def create_hospital(*,
                          hospital: schemas.Hospital = Body(..., descrption="Adds a new hospital"),
                          authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
    lat, lon = hospital.coordinates.split(',')
    # TODO setup action tupe creation
    headers = dict(Authorization=authorization)
    async with httpx.AsyncClient(headers=headers) as client:
        projects = await lookup(client, Resources.PROJECT.value, dict(name=hospital.name))
        if projects:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={"message": f"Hospital {hospital.name} already exists"})
        project = await new_resource(client,
                                     Resources.PROJECT,
                                     ResourceDocument(
                                         name=hospital.name,
                                         tags=[hospital.short_name],
                                         **dict(coordinates=[float(lat), float(lon)],
                                                plus_code=hospital.plus_code)).dict())

        application = ResourceDocument(
            name=hospital.name + ' Main app',
            tags=[hospital.short_name, 'main_app'],
            **dict(coordinates=[float(lat), float(lon)],
                   plus_code=hospital.plus_code)).dict()
        application['socialNetworks'] = {}
        application = await new_resource(client,
                                         '/'.join(
                                             [Resources.PROJECT.value, project['id'], Resources.APPLICATION.value]),
                                         application)

        out_hospital = hospital.dict()
        out_hospital['id'] = application['id']
        out_hospital['api_key'] = application['appApiKey']
        return out_hospital


@app.post("/hospitals/{hospital_name}/equipments")
async def create_product_category(*,
                                  hospital_name: str = Path(...,
                                                            description="Hospital Name"),
                                  product_category: schemas.ProductCategory = Body(...,
                                                                                   descrption="Adds a new hospital"),
                                  authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
    headers = dict(Authorization=authorization, ContentType='application/json')

    async with httpx.AsyncClient(headers=headers) as client:
        hospitals = await lookup(client, Resources.PROJECT.value, dict(name=hospital_name))
        if not hospitals:
            return JSONResponse(
                status_code=HTTP_404_NOT_FOUND,
                content={"message": f"Hospital {hospital_name} not found"})
        scopes = {
            "scopes": {
                "projects": [f'+{h["id"]}' for h in hospitals],
            }
        }

        products = await lookup(client, Resources.PRODUCT.value,
                                dict(identifiers=dict(name=name_to_identifier(product_category.name))))
        if len(products) > 1:
            return JSONResponse(status_code=HTTP_400_BAD_REQUEST,
                                content={"message": f"Product {product_category.name} is ambiguous"})
        elif len(products) == 1:
            product = await update_resource(client, Resources.PRODUCT, products[0]['id'], scopes)
        else:
            product_document = ResourceDocument(
                name=product_category.name,
                identifiers=dict(
                    category=name_to_identifier(product_category.product_category),
                    specification=name_to_identifier(product_category.specification),
                    name=name_to_identifier(product_category.name)),
                description=product_category.specification,
                tags=[product_category.specification]).dict()

            product_document['brand'] = product_category.brand
            product_document['categories'] = [product_category.product_category, product_category.specification]

            product = await new_resource(client,
                                         Resources.PRODUCT,
                                         hospitals[0]['id'],
                                         product_document)

            # await update_resource(client, Resources.PRODUCT, product['id'], scopes)
            redirection = await create_redirection(
                client,
                product['id'],
                'product',
                f'{HOSPITAL_HOST}/products/{product["id"]}')
            update_document = dict(customFields=dict(
                category=product_category.product_category,
                specification=product_category.specification))
            for k in redirection:
                update_document['customFields'][k] = redirection[k]

            await update_resource(client, Resources.PRODUCT, product['id'], update_document)

        return JSONResponse(status_code=HTTP_201_CREATED,
                            content={'brand': product['brand'],
                                     'name': product['name'],
                                     'createdAt': product['createdAt'],
                                     'product_category': product['categories'][0],
                                     'specification': product['description']},
                            headers=dict(Location=f'{EVT_HOST}/{Resources.PRODUCT.value}/{product["id"]}',
                                         ContentType='application/json'))


@app.get("/hospitals/{hospital_name}/equipments")
async def read_product_categories(*,
                                  hospital_name: str = Path(...,
                                                            description="Hospital Name"),
                                  authorization: str = Header(None, alias='Authorization',
                                                              convert_underscores=True),
                                  accept: str = Header(None, alias='Accept', convert_underscores=True),
                                  apiKey: str = Query(None)):
    headers = dict(Authorization=authorization if authorization else apiKey)

    async with httpx.AsyncClient(headers=headers) as client:

        api_key_access = await APIKey.api_key_information(client, hospital_name)
        if 'text/html' in set(accept.split(',')):
            table = ["""
            <div>
            """]
            urls = []

            async for r in download_resources(client=client, path=Resources.PRODUCT.value,
                                              project_id=api_key_access.project_id):
                urls.append(dict(url=r['customFields']['shortUrl'], label=r['customFields']['shortId']))

            for row_of_tags in tagging.next_row(8, 20, 1300, urls):
                row = []
                for tag in row_of_tags:
                    image_tag = f'<div style="display: inline-block"><img>{str(tag["qr"])}</img><br/>{tag["label"]}</div>'
                    row.append(image_tag)

                row.append("<br/>")
                table.append(''.join(row))

            table.append("""
                </div>
            """)
            return HTMLResponse('\n'.join(table))
        else:
            response_types_of_equipment = []
            async for r in download_resources(client=client, path=Resources.PRODUCT.value,
                                              project_id=api_key_access.project_id):

                d = {'name': r['name']}
                if 'brand' in r:
                    d['brand'] = r['brand']
                if 'customFields' in r:
                    d['product_category'] = r['customFields']['category']
                    d['specification'] = r['customFields']['specification']

                response_types_of_equipment.append(schemas.ProductCategory(**d))
            return response_types_of_equipment


@app.post("/hospitals/{hospital_name}/equipments/{product_name}")
async def create_equipment(*,
                           hospital_name: str = Path(..., description="Hospital Name"),
                           product_name: str = Path(...,
                                                    description="Product name. 'Any' creates a item without product assigned"),
                           equipment: Optional[schemas.Equipment] = Body(...,
                                                                         descrption="Equipment description"),
                           authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
    headers = dict(Authorization=authorization)

    async with httpx.AsyncClient(headers=headers) as client:
        hospitals = await lookup(client, Resources.PROJECT.value, dict(name=hospital_name))
        if not hospitals:
            return JSONResponse(
                status_code=HTTP_404_NOT_FOUND,
                content={"message": f"Hospital {hospital_name} not found"})
        scopes = {
            "scopes": {
                "projects": [f'+{h["id"]}' for h in hospitals],
            }
        }

        product_id = None
        if product_name != 'any':
            products = await lookup(client, Resources.PRODUCT.value,
                                    dict(identifiers=dict(name=name_to_identifier(product_name))))
            if len(products) > 1:
                return JSONResponse(status_code=HTTP_400_BAD_REQUEST,
                                    content={"message": f"Product {product_name} is ambiguous"})
            elif len(products) == 1:
                product_id = products.pop()['id']
            else:
                return JSONResponse(
                    status_code=HTTP_404_NOT_FOUND,
                    content={"message": f"Product  {product_name} not found"})
        if equipment.name and (await lookup(client, Resources.THNG.value, dict(name=equipment.name))):
            return JSONResponse(status_code=HTTP_400_BAD_REQUEST,
                                content={"message": f"Equipment name {equipment.name} exists"})
        if equipment.identifiers and (
                await lookup(client, Resources.THNG.value, dict(name=equipment.identifiers))):
            return JSONResponse(status_code=HTTP_400_BAD_REQUEST,
                                content={"message": f"Equipment identifiers {equipment.identifiers} exists"})
        if equipment.location and not (
                await lookup(client, Resources.PLACE.value, dict(name=equipment.location))):
            return JSONResponse(status_code=HTTP_404_NOT_FOUND,
                                content={"message": f"Location {equipment.location} does not exist"})
        thng_document = ResourceDocument(
            name=equipment.name,
            identifiers=equipment.identifiers,
            tags=['free'],
            description=equipment.description).dict()
        thng_document['product'] = product_id
        thng = await new_resource(client,
                                  Resources.THNG,
                                  hospitals[0]['id'],
                                  thng_document)
        await new_property(client, thng['id'], hospitals[0]['id'], 'inUse', False);
        redirection = await create_redirection(
            client,
            thng['id'],
            'thng',
            f'{HOSPITAL_HOST}/equipments/{thng["id"]}')
        update_document = dict(customFields={})
        for k in redirection:
            update_document['customFields'][k] = redirection[k]

        await update_resource(client, Resources.THNG, thng['id'], update_document)

        response_message = {'name': thng['name'],
                            'createdAt': thng['createdAt']}
        if 'description' in thng:
            response_message['description'] = thng['description']
        if 'location' in thng:
            response_message['location'] = thng['location']
        return JSONResponse(status_code=HTTP_201_CREATED,
                            content=response_message,
                            headers=dict(Location=f'{EVT_HOST}/{Resources.THNG.value}/{thng["id"]}',
                                         ContentType='application/json'))


@app.post("/hospitals/{hospital_name}/locations")
async def create_location(*,
                          hospital_name: str = Path(..., description="Hospital Name"),
                          dep_or_ward: schemas.DepartmentOrWard = Body(...,
                                                                       descrption="Dep/Ward"),
                          authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
    headers = dict(Authorization=authorization)

    async with httpx.AsyncClient(headers=headers) as client:
        hospitals = await lookup(client, Resources.PROJECT.value, dict(name=hospital_name))
        if not hospitals:
            return JSONResponse(
                status_code=HTTP_404_NOT_FOUND,
                content={"message": f"Hospital {hospital_name} not found"})
        if len(hospitals) != 1:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={"message": f"A location can only belong to one hospital, not  {len(hospitals)}"})
        hospital = hospitals.pop()
        scopes = {
            "scopes": {
                "projects": [f'+{hospital["id"]}'],
            }
        }

        locations = await lookup(client, Resources.PLACE.value,
                                 dict(identifiers=dict(name=name_to_identifier(dep_or_ward.name))))
        if len(locations) > 1:
            return JSONResponse(status_code=HTTP_400_BAD_REQUEST,
                                content={"message": f"Location with the name {dep_or_ward.name} already exists"})
        location_document = {
            "identifiers": {},
            "position": {
                "coordinates": hospital['customFields']['coordinates']
                ,
                "type": "Point"
            },
            'tags': hospital['tags'],
            "customFields": {}
        }
        response_dep_or_ward = {}
        for k in dep_or_ward.dict():
            if dep_or_ward.dict()[k] is None:
                continue
            if k == 'name':
                location_document[k] = dep_or_ward.dict()[k]
                location_document['identifiers'][k] = name_to_identifier(dep_or_ward.dict()[k])
            elif k == 'description':
                location_document[k] = dep_or_ward.dict()[k]
            else:
                location_document['customFields'][k] = dep_or_ward.dict()[k]
                location_document['identifiers'][k] = name_to_identifier(dep_or_ward.dict()[k])
            response_dep_or_ward[k] = dep_or_ward.dict()[k]

        location = await new_resource(client,
                                      Resources.PLACE,
                                      hospital['id'],
                                      location_document)
        await update_resource(client, Resources.PLACE, location['id'], scopes)

        return JSONResponse(status_code=HTTP_201_CREATED,
                            content=response_dep_or_ward,
                            headers=dict(Location=f'{EVT_HOST}/{Resources.PLACE.value}/{location["id"]}',
                                         ContentType='application/json'))


@app.get("/hospitals/{hospital_name}/locations", status_code=HTTP_200_OK)
async def read_location(*,
                        hospital_name: str = Path(..., description="Hospital Name"),
                        authorization: str = Header(None, alias='Authorization', convert_underscores=True),
                        accept: str = Header(None, alias='Accept', convert_underscores=True),
                        apiKey: str = Query(None)):
    headers = dict(Authorization=authorization if authorization else apiKey)

    async with httpx.AsyncClient(headers=headers) as client:
        # hospitals = await lookup(client, Resources.PROJECT.value, dict(name=hospital_name))
        # if not hospitals:
        #     return JSONResponse(
        #         status_code=HTTP_404_NOT_FOUND,
        #         content={"message": f"Hospital {hospital_name} not found"})
        # if len(hospitals) != 1:
        #     return JSONResponse(
        #         status_code=HTTP_400_BAD_REQUEST,
        #         content={"message": f"A location can only belong to one hospital, not  {len(hospitals)}"})
        # hospital = hospitals.pop()
        api_key_access = await APIKey.api_key_information(client, hospital_name)

        if 'text/html' in set(accept.split(',')):
            table = ["""
            <div>
            """]

            urls = []
            async for r in download_resources(client=client, path=Resources.PLACE.value,
                                              project_id=api_key_access.project_id):
                urls.append(dict(url=parse.urljoin(EVT_HOST, f"{Resources.PLACE.value}/{r['id']}"), label=r['name']))

            for row_of_tags in tagging.next_row(8, 20, 1300, urls):
                row = []
                for tag in row_of_tags:
                    image_tag = f'<div style="display: inline-block"><img>{str(tag["qr"])}</img><br/>{tag["label"]}</div>'
                    row.append(image_tag)

                row.append("<br/>")
                table.append(''.join(row))

            table.append("""
                </div>
            """)
            return HTMLResponse('\n'.join(table))
        else:
            response_deps_or_wards = []
            async for r in download_resources(client=client, path=Resources.PLACE.value,
                                              project_id=api_key_access.project_id):
                d = {'name': r['name']}
                if 'description' in r:
                    d['description'] = r['description']
                if 'customFields' in r:
                    for k in r['customFields']:
                        d[k] = r['customFields'][k]
                response_deps_or_wards.append(schemas.DepartmentOrWard(**d))
            return response_deps_or_wards


#
# @app.get("/hospitals/{hospital_name}/locations")
# async def read_location(*,
#                         hospital_name: str = Path(..., description="Hospital Name"),
#                         apiKey: str = Query(None)):
#     headers = dict(Authorization=apiKey)
#
#     async with httpx.AsyncClient(headers=headers) as client:
#
#         api_key_access = await APIKey.api_key_information(client, hospital_name)
#


@app.get("/{page}")
async def read_file(*,
                    page: str = Path(..., regex='\w+\.html$', description="COVID-19 related site")):
    # thngId: str = Query(default="", description="Thnd id")):

    return FileResponse(os.path.join('web', page))


@app.get("/{folder}/{page}")
async def _(*, folder: str = Path(..., description="folder"),
            page: str = Path(..., description="COVID-19 related site")):
    return HTMLResponse(os.path.join('web', folder, page))


#
@app.get("/{folder}/{folder2}/{page}")
async def _(*, folder: str = Path(..., description="folder"),
            folder2: str = Path(..., description="folder"),
            page: str = Path(..., description="COVID-19 related site")):
    return FileResponse(os.path.join('web', folder, folder2, page))
#
# @app.get('/debug/{hospital_name}')
# async def _(*, hospital_name: str = Path(..., description="Hospital Name"), apiKey: str = Query(...)):
#     headers = dict(Authorization=apiKey
#                    )
#     async with httpx.AsyncClient(headers=headers) as client:
#         api_key_access = await APIKey.api_key_information(client, hospital_name)
#
#         urls = []
#         async for r in download_resources(client=client, path=Resources.PLACE.value,
#                                           project_id=api_key_access.project_id):
#             urls.append(parse.urljoin(EVT_HOST, f"{Resources.PLACE.value}/{r['id']}"))
#
#         tagging.next_row(10, 100, 3000, urls)
#
#
# @app.get('/debug')
# async def _(authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
#     headers = dict(Authorization=authorization)
#     async with httpx.AsyncClient(headers=headers) as client:
#         return await APIKey.new_api_key(client)
#     hospitals = await lookup(client, Resources.PROJECT.value, dict(name='Nightingale 2020 - ExCeL London'))
#     return hospitals.pop()

# return key for tag or include some token in thgn redirection that is updated after every call
