import copy
import json
import os
import time
from difflib import SequenceMatcher

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
import re
from app import (
    config_parser as cp,
    htmllib,
)


class Translator:
    def __init__(self, client, config: cp.BookConfig, model_name):
        self._html_para_end = '</p>'
        self._html_doc_end = '</html>'
        self._max_chunk_size = 5500
        self._agen_client = client
        self._input_path = config.get_input()
        self._output_path = config.get_output()
        self._from_lang = config.get_from_lang()
        self._to_lang = config.get_to_lang()
        self._is_test_item = config.get_test_item()
        self._promote = config.get_promote()
        self._from_chapter = config.get_from_chapter()
        self._to_chapter = config.get_to_chapter()
        self._model_name = model_name

    def _is_content_match(self, src1, src2):
        src1 = src1.replace('\n', '').replace('\t', '').replace('\r', '')
        src2 = src2.replace('\n', '').replace('\t', '').replace('\r', '')
        score = SequenceMatcher(None, src1, src2).quick_ratio()
        return score > 0.99

    def _split_html_by_sentence(self, content):
        abbreviations = ['vs', 'dr', 'mr', 'mrs', 'ms', 'prof', 'inc', 'ltd', 'jr', 'sr', 'etc', 'e.g', 'i.e']
        abbreviation_patterns = {abbr: f"{abbr.upper()}_ABBR" for abbr in abbreviations}
        # 构建正则表达式
        pattern = re.compile(r'(?<!\b[A-Za-z]\.)(?<=\.|\?|\!)\s+')
        # 替换缩写为标记
        for abbr, marker in abbreviation_patterns.items():
            content = re.sub(r'\b' + re.escape(abbr) + r'\.', marker, content, flags=re.IGNORECASE)
        sentence_lst = pattern.split(content)
        for i in range(len(sentence_lst)):
            for abbr, marker in abbreviation_patterns.items():
                sentence_lst[i] = sentence_lst[i].replace(marker, abbr + '.')
        chunks = []
        current_chunk = ""
        for i, sentence in enumerate(sentence_lst):
            if len(sentence) > self._max_chunk_size:
                chunks.append(current_chunk)
                tag_lst = self._split_html_by_paragraph(sentence)
                chunks.extend(tag_lst)
                current_chunk = ''
            elif (len(current_chunk) > self._max_chunk_size):
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence
            if i == len(sentence_lst) - 1:
                chunks.append(current_chunk)
                break
        assert ''.join(chunks) == ''.join(sentence_lst)
        if self._is_test_item > 0:
            chunks = chunks[:self._is_test_item]
        return chunks

    def _preprocess_html_content(self, content):
        tag_list0 = htmllib.parse_html_to_tags_and_content(content)
        tag_list = []
        for tag_str in tag_list0:
            if (
                    htmllib.is_span_tag_without_id(tag_str) or
                    htmllib.is_italy_tag(tag_str) or
                    htmllib.is_tt_tag(tag_str)
            ):
                continue
            tag_list.append(tag_str)
            if htmllib.is_span_tag_with_id(tag_str):  # 前面删除了</span>，在这里加入.
                tag_list.append('</span>')
        return ''.join(tag_list)

    def _split_html_by_paragraph(self, content):
        tag_list = htmllib.parse_html_to_tags_and_content(content)
        new_parap_lst = []
        for i, para in enumerate(tag_list):
            new_parap_lst.append(para)

        para_count = len(new_parap_lst)
        new_parap_lst2 = []
        i = 0
        while i < para_count:
            sub_para = []
            j = 0
            while len(''.join(sub_para)) < self._max_chunk_size and i < para_count:
                sub_para.append(new_parap_lst[i])
                j += 1
                i += 1
            new_parap_lst2.append(''.join(sub_para))
        if self._is_test_item > 0:
            new_parap_lst2 = new_parap_lst2[:self._is_test_item]
        return new_parap_lst2

    def _is_need_retry(self, src_tags, translated_tags, retry_times):
        img1_count = 0
        img2_count = 0
        need_retry = False
        for tag in src_tags:
            if htmllib.is_img_tag(tag):
                img1_count += 1
        for tag in translated_tags:
            if htmllib.is_img_tag(tag):
                img2_count += 1
        if (img1_count != img2_count) and retry_times < 5:
            retry_times += 1
            need_retry = True
        if translated_tags[0] != '<div>' or translated_tags[-1] != '</div>':
            need_retry = True
        return need_retry, retry_times

    def _translate_chunk(self, src_html, last_message):
        input_txt = f'<div>{src_html}</div>'
        last_message_copy = copy.deepcopy(last_message)
        last_message_copy.extend(
            [
                {'role': 'system', 'content': self._promote},
                {'role': 'user', 'content': input_txt},
            ]
        )
        retry_times = 0
        while True:
            response = self._agen_client.chat.completions.create(
                model=self._model_name,
                temperature=1.1,
                messages=last_message_copy,
                stream=False,
            )
            translated_text = response.choices[0].message.content
            tag1_lst = htmllib.parse_html_to_tags_and_content(input_txt)
            tag2_lst = htmllib.parse_html_to_tags_and_content(translated_text)
            need_retry, retry_times = self._is_need_retry(src_tags=tag1_lst, translated_tags=tag2_lst,
                                                          retry_times=retry_times)
            if not need_retry:
                translated_text = ''.join(tag2_lst[1:-1])
                break
            time.sleep(0.01)
        new_last_message = last_message[-3:]
        new_last_message.append(
            {
                'role': response.choices[0].message.role,
                'content': input_txt,  # response.choices[0].message.content,
            }
        )
        return translated_text, new_last_message

    def _make_checkpoint_path(self, input_epub_path, from_lang, to_lang):
        file_name = os.path.splitext(os.path.basename(input_epub_path))[0]
        new_name = f'{file_name}_{from_lang.lower()}_{to_lang.lower()}.json'
        new_path = os.path.join('checkpoint', new_name)
        return new_path

    def _read_checkpoint_info(self, input_epub_path, from_lang, to_lang):
        cp_path = self._make_checkpoint_path(input_epub_path, from_lang, to_lang)
        check_info = {}
        if os.path.exists(cp_path):
            check_info = json.load(open(cp_path, 'r'))
        return check_info

    def _write_checkpoint_info(self, chapter, chunk):
        check_info = self._read_checkpoint_info(self._input_path, self._from_lang, self._to_lang)
        check_info['chapter'] = chapter
        check_info['chunk'] = chunk
        return check_info

    def _write_chapter_html(self, current_chapter, translated_text):
        file_name = os.path.splitext(os.path.basename(self._input_path))[0]
        new_name = f'{file_name}_{self._from_lang.lower()}_{self._to_lang.lower()}_cha{current_chapter}.html'
        new_path = os.path.join('checkpoint', new_name)
        with open(new_path, 'w') as fd:
            fd.write(translated_text)
        return new_path

    @staticmethod
    def _get_chapters_count(book):
        count = 0
        for i in book.get_items():
            if i.get_type() == ebooklib.ITEM_DOCUMENT:
                count += 1
        return count

    @staticmethod
    def _try_repair_translated_html(raw_html, translated_html):
        is_end = raw_html.find('</html>') != -1
        translated_html = translated_html.strip().strip("'''")
        translated_html = translated_html.replace('</body>', '').replace('</html>', '')
        if is_end:
            translated_html += '</body></html>'
        return translated_html

    def _has_over_max_chunk_size(self, chunk_lst):
        has = False
        for chunk in chunk_lst:
            if len(chunk) > self._max_chunk_size * 2:
                has = True
                break
        return has

    def _translate_one_chapters(self, content_bin, chapter, check_point_info):
        content = content_bin.decode('utf-8')
        content = self._preprocess_html_content(content)
        translated_chunks = []
        chunks = self._split_html_by_sentence(content)
        # chunks = self._split_html_by_paragraph(content)
        over_max_size = self._has_over_max_chunk_size(chunks)
        assert not over_max_size
        start_chunk = check_point_info.get(f'chapter_{chapter}', 0)
        last_message = []
        for j, chunk in enumerate(chunks[start_chunk:]):
            chunk_idx = j + start_chunk
            print("Translating chunk %d/%d..." % (chunk_idx + 1, len(chunks)))
            print('=============Raw Content===============')
            print(chunk)
            if htmllib.is_tag_no_string(chunk):
                translated_text, last_message = self._translate_chunk(chunk, last_message)
            else:
                translated_text = chunk
            translated_chunks.append(translated_text)
            # self._write_checkpoint_info(chapter=chapter, chunk=chunk_idx)
            print('>>>>>>>>>>>>>Translated Text<<<<<<<<<<<')
            print(translated_text)
        translated_text = ''.join(translated_chunks)  # ''.join(tag_list)
        print(f'{chapter}章节内容:')
        print(translated_text)
        print('******************************')
        self._write_chapter_html(chapter, translated_text)
        return translated_text

    def _is_wanted_chapter(self, chapter, from_chapter, to_chapter):
        return chapter >= from_chapter and chapter <= to_chapter

    def translate(self):
        book = epub.read_epub(self._input_path)
        current_chapter = 1
        # todo: get checkpoint info
        chapters_count = self._get_chapters_count(book)
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            assert item.get_type() == ebooklib.ITEM_DOCUMENT
            wanted_chapter = self._is_wanted_chapter(current_chapter, self._from_chapter, self._to_chapter)
            if not wanted_chapter:
                current_chapter += 1
                continue
            print("正在翻译: %d/%d ..." % (current_chapter, chapters_count))
            translated_text = self._translate_one_chapters(item.content, current_chapter, check_point_info={})
            item.content = translated_text.encode('utf-8')
            current_chapter += 1
        epub.write_epub(self._output_path, book, {})

    def _make_chapter_digest(self, content):
        lines = content[0:250].split('\n')
        line_lst = []
        for l in lines:
            l = l.strip()
            if not l:
                continue
            line_lst.append(l)
        return '\n'.join(line_lst)

    def show_chapters(self):
        book = epub.read_epub(self._input_path)
        current_chapter = 1
        chapters_count = self._get_chapters_count(book)
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            print(">>>>章节：%d/%d (字符：%d)<<<<" % (current_chapter, chapters_count, len(item.content)))
            soup = BeautifulSoup(item.content, 'html.parser')
            beginning = self._make_chapter_digest(soup.text)
            print(beginning)
            print('')
            current_chapter += 1

    def _check_unused_image(self, book):
        image_lst = []
        for image in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            image_lst.append(image.file_name)
        html_lst = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.content, 'html.parser')
            html_lst.append(str(soup))
        unused_img_lst = []
        for img in image_lst:
            find = False
            for html in html_lst:
                if html.find(img) != -1:
                    find = True
                    break
            if not find:
                unused_img_lst.append(img)
        return unused_img_lst

    def check_error(self):
        book = epub.read_epub(self._input_path)
        self._check_unused_image(book)


if __name__ == '__main__':
    with open('checkpoint/TradingAndExchanges_en_zh_cha41.html', 'r') as fd:
        content = fd.read()
        Translator._try_repair_translated_html(None, content)
