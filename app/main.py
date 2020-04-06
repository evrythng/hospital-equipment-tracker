from __future__ import absolute_import, division, print_function, unicode_literals

import os
from typing import Optional

import httpx

from starlette.responses import HTMLResponse, UJSONResponse as JSONResponse, FileResponse

from evrythng import Resources, ResourceDocument, new_resource, lookup, update_resource, EVT_HOST, create_redirection, \
    name_to_identifier, new_property

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
            await create_redirection(
                client,
                product['id'],
                'product',
                f'{HOSPITAL_HOST}/products/{product["id"]}')

        return JSONResponse(status_code=HTTP_201_CREATED,
                            content={'brand': product['brand'],
                                     'name': product['name'],
                                     'createdAt': product['createdAt'],
                                     'product_category': product['categories'][0],
                                     'specification': product['description']},
                            headers=dict(Location=f'{EVT_HOST}/{Resources.PRODUCT.value}/{product["id"]}',
                                         ContentType='application/json'))


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

        await create_redirection(
            client,
            thng['id'],
            'thng',
            f'{HOSPITAL_HOST}/equipments/{thng["id"]}')
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


@app.get("/{page}")
async def read_file(*,
                    page: str = Path(default='', description="COVID-19 related site")):
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


@app.get('/debug')
async def _(authorization: str = Header(None, alias='Authorization', convert_underscores=True)):
    headers = dict(Authorization=authorization)
    async with httpx.AsyncClient(headers=headers) as client:
        hospitals = await lookup(client, Resources.PROJECT.value, dict(name='Nightingale 2020 - ExCeL London'))
        return hospitals.pop()

# return key for tag or include some token in thgn redirection that is updated after every call
