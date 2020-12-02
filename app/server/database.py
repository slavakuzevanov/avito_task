import motor.motor_asyncio

MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient('db', port=27017)

database = client.avito_db

statistics_collection = database.get_collection("avito_tb")


# helpers


def structure_helper(statistics) -> dict:
    return {
        "id": statistics["_id"],
        "region": statistics["region"],
        "q": statistics["q"],
        "list": statistics["list"]
    }


# Count all documents in table
async def do_count_all() -> int:
    n = await database.avito_tb.count_documents({})
    return n


# Count documents by pair of region and q
async def do_count_by_region_q(region: str, q: str) -> int:
    n = await database.avito_tb.count_documents({'region': region, 'q': q})
    return n


# Retrieve a document with a matching pair of region and q
async def do_find_one_by_region_q(region: str, q: str) -> dict:
    document = await database.avito_tb.find_one({'region': region, 'q': q})
    return structure_helper(document)


# Retrieve all document from collection
async def do_find_all() -> list:
    documents = []
    async for document in statistics_collection.find():
        documents.append(structure_helper(document))
    return documents


# Retrieve a document with a matching ID
async def do_find_one_by_id(id: int) -> dict:
    document = await database.avito_tb.find_one({'_id': id})
    return structure_helper(document)


# Insert document
async def insert_document(id: int, region: str, q: str, info_dict: dict):
    document = {'_id': id, 'region': region, 'q': q, 'list': [info_dict]}
    await database.avito_tb.insert_one(document)


# Update document
async def update_document(id: int, data: list) -> None:
    await statistics_collection.update_one({"_id": id}, {"$set": {'list': data}})
