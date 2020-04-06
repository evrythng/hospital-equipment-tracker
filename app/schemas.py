from pydantic import BaseModel, Field
from typing import Optional, List


class Hospital(BaseModel):
    name: str = Field(..., description="The full hospital name")
    short_name: str = Field(..., description="Hospital short name used as resource name")
    # id:Optional[str] = Schema(..., description="Unique hospital ID")
    plus_code:str = Field(..., description="Google Plus code to fetch the address")
    # api_key: Optional[str] = Schema(..., description="Trusted app Api key")
    coordinates:str = Field(None, description="Coorindates of the hospital")

class ProductCategory(BaseModel):
    name: str = Field(..., description="Product name")
    brand: str = Field(..., description="Product brand")
    specification: str = Field(..., description="Product specification")
    product_category: str = Field(..., description="Product product_category")

class Equipment(BaseModel):
    name: Optional[str] = Field(None, description="Equipment name or label")
    identifiers: Optional[dict] = Field(None, description="Equipment identifiers")
    description: Optional[str] = Field(None, description="Product description")
    location: Optional[str]= Field(None, description="Where this item is located")


class DepartmentOrWard(BaseModel):
    name: str = Field(..., description="Place name")
    location_identifier:str = Field(None, description="Room number, etc")
    type: str = Field(None, description="Type of location")
    service: str = Field(None, description="Medical service")
    floor: str = Field(None, description="Floor where this place is located")
    building: str = Field(None, description="Building where this place is located")
    cardinal_direction: str = Field(None, description="Which direction this place is located")
    colour: str = Field(None, description="Field to support colour labeling")
    description: Optional[str] = Field(None, description="Place description")
