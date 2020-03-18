from src.csv2json import reformat_csv, process_file
from unittest.mock import patch
from tests.mock_curie_list import mock_curies
import copy
import json



def test_csv_to_json_format():
    csv_file = 'data/test-synonyms.csv'
    lines = []
    with open(csv_file) as file:
        lines = file.readlines()

    formatted = reformat_csv(csv_file)
    assert len(lines) - 1 == len(formatted)
    assert 'curie' in formatted[0]
    assert 'name' in formatted[0]
    assert 'id' in formatted[0]
    assert 'length' in formatted[0]


def test_replace_with_preferred_id():

    def json_dumps_mock(data, fp):
        to_replace_curies = [f"curie={x['curie']}" for x in mock_curies]
        node_norm_url = f'https://nodenormalization-sri.renci.org/' \
                        f'get_normalized_nodes?{"&".join(to_replace_curies)}'
        import requests
        response = requests.get(node_norm_url).json()
        normalized = [response[curie]['id']['identifier'] for curie in response]
        #
        supposed_to_be_normalized = [d['curie'] for d in data]

        for n, s_n in zip(normalized, supposed_to_be_normalized):
            assert n == s_n

    with patch('src.csv2json.reformat_csv', lambda x : copy.deepcopy(mock_curies)):
        with patch('json.dumps', json_dumps_mock):
            process_file('this_does_not_matter.patched', 'out.json' )
