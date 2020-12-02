from datetime import datetime

import pymongo
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every

from server.database import (
    do_count_all,
    do_count_by_region_q,
    do_find_one_by_region_q,
    insert_document,
    do_find_one_by_id,
    do_find_all,
    MONGO_DETAILS
)
from server.models.responsemodels import (
    ErrorResponseModel,
    ResponseModel
)


app = FastAPI()


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to this fantastic app!"}


@app.get("/add", tags=["Statistics"], response_description="Pair of region and q added into the database")
async def add(region: str, q: str):
    n = await do_count_by_region_q(region, q)

    if n == 0:
        id = await do_count_all() + 1

        result = requests.get(f'https://www.avito.ru/{region}?q={q}')
        html = result.text
        soup = BeautifulSoup(html, 'lxml')
        kolvo = soup.find('span', class_='page-title-count-1oJOc').string
        # считать информацию с сайта
        top5 = [
            {
                'title': section.find('span', itemprop='name').string,
                'href': section.find('a', itemprop='url').get('href'),
                'price': section.find('meta', itemprop='price').get('content') + ' ' +
                         section.find('meta', itemprop='priceCurrency').get('content')
            } for section in soup.find_all('div', class_='iva-item-root-G3n7v', limit=5)
        ]

        info_dict = {'timestamp': int(datetime.now().timestamp()), 'count': kolvo, 'top5': top5}

        await insert_document(id, region, q, info_dict)
        return ResponseModel({'id': id}, "Pair of region and q added successfully.")
    else:
        document = await do_find_one_by_region_q(region, q)
        id = document['id']
        return ResponseModel({'id': id}, "Pair of region and q already in database.")


@app.get("/stat", tags=["Statistics"], response_description="Statistics")
async def get_stats(id: int, interval: str):
    try:
        start_time, end_time = interval.split('/')
        start_time = int(datetime.strptime(start_time, "%Y.%m.%d %H:%M:%S").timestamp())
        end_time = int(datetime.strptime(end_time, "%Y.%m.%d %H:%M:%S").timestamp())
    except:
        return ErrorResponseModel('Bad Request', 400,
                                  'Interval should be in the form YYYY.MM.DD HH:MM:SS/YYYY.MM.DD HH:MM:SS')
    try:
        document = await do_find_one_by_id(id)
    except:
        return ErrorResponseModel('Bad Request', 400, 'No such id in the database')
    result = []
    for item in document['list']:
        if end_time >= item['timestamp'] >= start_time:
            result.append({'count': item['count'], 'timestamp': item['timestamp']})
    return ResponseModel(result, 'Statistics received')


@app.get("/top5", tags=["Statistics"], response_description="Statistics")
async def get_top5(id: int):
    try:
        document = await do_find_one_by_id(id)
    except:
        return ErrorResponseModel('Bad Request', 400, 'No such id in the database')
    result = {'timestamp': document['list'][-1]['timestamp'], 'top5': document['list'][-1]['top5']}
    return ResponseModel(result, 'Top5 products received')


@app.on_event('startup')
@repeat_every(seconds=60 * 60, wait_first=True)  # 1 hour
def add_new_info_to_db() -> None:
    client = pymongo.MongoClient('avito_mongodb', port=27017)
    database = client.avito_db
    collection = database['avito_tb']
    for item in collection.find({}):
        list = item['list']
        # считать информацию с сайта
        result = requests.get(f'https://www.avito.ru/{item["region"]}?q={item["q"]}')
        html = result.text
        soup = BeautifulSoup(html, 'lxml')
        kolvo = soup.find('span', class_='page-title-count-1oJOc').string
        top5 = [
            {
                'title': section.find('span', itemprop='name').string,
                'href': section.find('a', itemprop='url').get('href'),
                'price': section.find('meta', itemprop='price').get('content') + ' ' +
                         section.find('meta', itemprop='priceCurrency').get('content')
            } for section in soup.find_all('div', class_='iva-item-root-G3n7v', limit=5)
        ]

        list.append({'timestamp': int(datetime.now().timestamp()), 'count': kolvo, 'top5': top5})
        collection.update_one({'_id': item['_id']}, {'$set': {'list': list}})
    print('Task is done!')
