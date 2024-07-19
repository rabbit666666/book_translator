import re
from bs4 import BeautifulSoup

def parse_html_to_tag_tuples2(html_code):
    # Regular expression to match HTML tags and content between them
    tag_pattern = re.compile(r'(<!--.*?-->|<[^>]+>|[^<]+)')
    matches = tag_pattern.findall(html_code)
    # Remove empty strings and strip whitespaces from the content
    matches = [item.strip() for item in matches if item.strip()]
    # Group tags and content
    tag_tuples = []
    current_tag = ''
    current_content = ""
    for item in matches:
        if item.startswith('<') and not item.startswith('</'):
            if current_tag:
                tag_tuples.append(current_tag + current_content)
            current_tag = item
            current_content = ""
        elif item.startswith('</'):
            if current_tag:
                tag_tuples.append(current_tag + current_content + item)
                current_tag = ''  # None
                current_content = ""
            else:
                tag_tuples.append(current_content + item)
                current_content = ""
        else:
            current_content += item
    # Handle case where the last tag has no closing tag
    if current_tag:
        tag_tuples.append(current_tag + current_content)
    return tag_tuples

def parse_html_to_tag_tuples(html_code):
    # Regular expression to match HTML tags and content between them
    tag_pattern = re.compile(r'(<!--.*?-->|<[^>]+>|[^<]+)')
    matches = tag_pattern.findall(html_code)
    # Remove empty strings and strip whitespaces from the content
    matches = [item.strip() for item in matches if item.strip()]
    # Group tags and content
    tag_tuples = []
    current_tag = ''
    current_content = ""
    for item in matches:
        if item.startswith('<') and not item.startswith('</'):
            if current_tag:
                tag_tuples.append(current_tag + current_content)
            current_tag = item
            current_content = ""
        elif item.startswith('</'):
            if current_tag:
                tag_tuples.append(current_tag + current_content + item)
                current_tag = ''  # None
                current_content = ""
            else:
                tag_tuples.append(current_content + item)
                current_content = ""
        else:
            current_content += item
    # Handle case where the last tag has no closing tag
    if current_tag:
        tag_tuples.append(current_tag + current_content)
    return tag_tuples


def parse_html_to_tags_and_content(html_code):
    # Regular expression to match HTML tags and content between them
    tag_pattern = re.compile(r'(<!--.*?-->|<[^>]+>|[^<]+)')
    tags_and_content = tag_pattern.findall(html_code)
    # Remove empty strings and strip whitespaces from the content
    tags_and_content = [item.strip() for item in tags_and_content if item.strip()]
    return tags_and_content

def is_html_tag(s):
    # Regular expression to match HTML tags
    tag_pattern = re.compile(r'<[^>]+>')
    return bool(tag_pattern.fullmatch(s))

def align_html_tags(html1, html2):
    # tag1_lst = parse_html_to_tags_and_content(html1)
    tag2_lst = parse_html_to_tags_and_content(html2)
    assert tag2_lst[0] == '<div>' and tag2_lst[-1] == '</div>'
    return ''.join(tag2_lst[1:-1])

def is_tag_no_string(tag):
    text = BeautifulSoup(tag, 'html.parser').text
    return not not text.strip()

def is_italy_tag(tag):
    start_tag = tag.lower() == '<i>'
    end_tag = tag.lower() == '</i>'
    return start_tag or end_tag

def is_tt_tag(tag):
    start_tag = tag.lower() == '<tt>'
    end_tag = tag.lower() == '</tt>'
    return start_tag or end_tag


def is_span_tag_without_id(tag):
    # 正则表达式匹配开头的 <span> 或 </span> 标签，并且不含有 id 属性
    open_span_pattern = re.compile(r'<span\b(?![^>]*\bid=)[^>]*>', re.IGNORECASE)
    close_span_pattern = re.compile(r'</span>', re.IGNORECASE)
    return bool(open_span_pattern.search(tag) or close_span_pattern.search(tag))


def is_span_tag_with_id(tag):
    # 正则表达式匹配开头的 <span> 标签，并且含有 id 属性
    span_with_id_pattern = re.compile(r'<span\b[^>]*\bid=[\'"][^\'"]*[\'"][^>]*>', re.IGNORECASE)
    return bool(span_with_id_pattern.search(tag))

def is_img_tag(tag):
    # 正则表达式匹配 <img> 标签
    img_pattern = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
    return bool(img_pattern.search(tag))
