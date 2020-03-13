from collections import defaultdict
import csv
import json
import asyncio
import aiohttp
import os

csv_file_name = os.environ.get('CSV_FILE_NAME')
json_out_name = os.environ.get('JSON_FILE_NAME')


def reformat_csv(csv_file_name: str) -> list:
    output = []
    with open(csv_file_name, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        # skip header
        next(reader)
        for idx, row in enumerate(reader):
            entity_id = ':'.join(row[0].split('/')[-1].split('_'))
            name = row[-1]
            output.append({
                'id': idx,
                'curie': entity_id,
                'name': name,
                'length': len(name)
            })
    return output


async def async_get_json(url, headers={}):
    """
        Gets json response from url asyncronously.
    """
    async with aiohttp.ClientSession() as session :
        try:
            async with session.get(url, headers= headers) as response:
                if response.status != 200:
                    print(f"Failed to get response from {url}. Status code {response.status}")
                    return {}
                return await response.json()
        except:
            print(f"Failed to get response from {url}." )
            return {}


async def get_main_ids(id_list):
    node_normalization_base_url = 'https://nodenormalization-sri.renci.org/get_normalized_nodes?'
    curie_params = '&'.join(map(lambda x: f'curie={x}', id_list))
    result = await async_get_json(f'{node_normalization_base_url}{curie_params}')
    # if we have things back create a dict map for converting things to the main ids
    curie_map = {}

    if result:
        for curie in result:
            item = result[curie]
            if item:
                main_curie = item.get('id').get('identifier')
                if main_curie and main_curie != curie:
                    curie_map[curie] = main_curie
    return curie_map


async def convert_chunks_to_map(named_items_list):
    tasks = []
    all_curies = set()
    for x in named_items_list:
        all_curies.add(x['curie'])
    # all_curies = set(map(lambda x: x['curie'], named_items_list))
    # chunk em up in thousands
    chunck_size = 1000
    all_curies = list(all_curies)
    chunks = [all_curies[start: start + chunck_size] for start in range(0, len(all_curies), chunck_size)]
    for chunk in chunks:
        tasks.append(get_main_ids(chunk))
    results = await asyncio.gather(*tasks)
    # merge results
    merged_map = {curie: curie_mapped_to[curie] for curie_mapped_to in results for curie in curie_mapped_to}
    return merged_map


def process_file(csv_file_name:str, json_out_name: str):
    csv_reformatted = reformat_csv(csv_file_name)
    event_loop = asyncio.get_event_loop()
    curie_map = event_loop.run_until_complete(convert_chunks_to_map(csv_reformatted))
    for item in csv_reformatted:
        # if curie is  found in the normalized map use that mapping else stay
        replacement = curie_map.get(item['curie'], None)
        if replacement:
            print('replacing ', item['curie'], 'with', replacement)
            item['curie'] = replacement
    # json dumps
    with open(json_out_name, 'w') as out_file:
        json.dump(csv_reformatted, out_file, indent=4)


if __name__=='__main__':
    process_file(csv_file_name, json_out_name)
