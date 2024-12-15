import os
from typing import List, Any

import motor.motor_asyncio

from dotenv import load_dotenv
from pydantic import BaseModel
from app.models.user import User
from app.models.requests import Requests


load_dotenv()


client = motor.motor_asyncio.AsyncIOMotorClient(
    f'mongodb://{os.getenv("MONGO_USERNAME")}:{os.getenv("MONGO_PASSWORD")}@{os.getenv("MONGO_HOST")}:{os.getenv("MONGO_PORT")}')
raw_db = client[os.getenv("MONGO_DB_NAME")]

external_client = motor.motor_asyncio.AsyncIOMotorClient(
    f'mongodb://{os.getenv("MONGO_USERNAME")}:{os.getenv("MONGO_PASSWORD")}@{os.getenv("MONGO_HOST_EXTERNAL")}:{os.getenv("MONGO_PORT_EXTERNAL")}')
external_db = external_client[os.getenv("MONGO_DB_NAME")]


class Collection:

    def __init__(self, model, collection_name: str):
        self.collection = client[os.getenv("MONGO_DB_NAME")][collection_name]
        self.model = model

    async def find_one(self, f: dict):
        data = await self.collection.find_one(f)
        if not data:
            return None
        data['_id'] = str(data['_id'])
        model = self.model(**data)
        return model

    async def find(self, f: dict, count: int = 100000, offset: int = 0) -> List:
        cursor = self.collection.find(f).skip(offset).limit(count)
        data = await cursor.to_list(length=count)
        list_models = []
        for item in data:
            item['_id'] = str(item['_id'])
            list_models.append(self.model(**item))
        return list_models

    async def update_one(self, f: dict, s: dict, upsert: bool = False):
        res = await self.collection.update_one(f, {'$set': s}, upsert=upsert)
        return res

    async def delete_one(self, f: dict, ):
        res = await self.collection.delete_one(f)
        return res

    async def delete_many(self, f: dict, ):
        res = await self.collection.delete_many(f)
        return res

    async def update_many(self, f: dict, s: dict):
        res = await self.collection.update_many(f, s)
        return res

    async def count(self, f: dict):
        res = await self.collection.count_documents(f)
        return res

    async def insert_one(self, i: dict):
        res = await self.collection.insert_one(i)
        return res


class MongoDbClient(BaseModel):
    users: Any
    requests: Any


db = MongoDbClient(
    users=Collection(collection_name='users', model=User),
    requests=Collection(collection_name='requests', model=Requests)

)
