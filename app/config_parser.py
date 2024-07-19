import json5


class BookConfig:
    def __init__(self, book_cfg):
        self._action = book_cfg.get('action')
        self._input = book_cfg.get('input')
        self._output = book_cfg.get('output')
        self._continue = book_cfg.get('continue')
        self._test_item = book_cfg.get('test')
        self._from_chapter = book_cfg.get('from_chapter')
        self._to_chapter = book_cfg.get('to_chapter')
        self._from_lang = book_cfg.get('from_lang')
        self._to_lang = book_cfg.get('to_lang')
        self._promote = book_cfg.get('promote')
        if not self._promote:
            self._promote = [
                "1. You are an %s-to-%s translator. " % (self._from_lang, self._to_lang),
                "2. Keep all special characters and HTML tags as in the source text. ",
                "3. Return only %s translation. Don't add extra HTML tag!!!" % self._to_lang
            ]
        self._promote = '\n'.join(self._promote)

    def get_action(self):
        return self._action

    def get_input(self):
        return self._input

    def get_output(self):
        return self._output

    def get_continue(self):
        return self._continue

    def get_test_item(self):
        return self._test_item

    def get_from_chapter(self):
        return self._from_chapter

    def get_to_chapter(self):
        return self._to_chapter

    def get_from_lang(self):
        return self._from_lang

    def get_to_lang(self):
        return self._to_lang

    def get_promote(self):
        return self._promote
