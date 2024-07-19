import argparse
import os

import json5
from openai import OpenAI

from app import (config_parser as cp, translator)


def read_config(config_file):
    with open(config_file, 'r') as f:
        config = json5.load(f)
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='App to translate or show chapters of a book.')

    parser.add_argument('--config', required=True, help='配置文件')
    args = parser.parse_args()

    config_json = read_config(args.config)
    os.environ['OPENAI_BASE_URL'] = config_json['openai']['url']
    api_key = config_json['openai']['api_key']
    for book in config_json['books']:
        if not book['run']:
            continue
        openai_client = OpenAI(api_key=api_key,
                               base_url=None)
        book_cfg = cp.BookConfig(book)
        translator = translator.Translator(client=openai_client, config=book_cfg,
                                           model_name=config_json['openai']['model_name'])
        action = book_cfg.get_action()
        if action == 'translate':
            translator.translate()
        elif action == 'show_chapters':
            translator.show_chapters()
        elif action == 'check_error':
            translator.check_error()
        else:
            assert False, f'Unknown Action:{action}'
