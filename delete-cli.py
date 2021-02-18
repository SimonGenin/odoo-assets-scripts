import pickle
import re
import os
import argparse
import sys

def update_path(items):
    news = []
    for a, b, c, d, e, f, path in items:

        enterprise = "../enterprise/" + path
        base = "../community/odoo/addons/" + path
        community = "../community/addons/" + path

        if os.path.exists(enterprise):
            news.append((a, b, c, d, enterprise))
        elif os.path.exists(base):
            news.append((a, b, c, d, base))
        elif os.path.exists(community):
            news.append((a, b, c, d, community))
        else:
            print("FUCK =>", a, b, c, d, e, f, path)
    return news

def get_data(modules):
    with open('results.pickle', 'rb') as handle:
        items = pickle.load(handle)
    items = [item for item in items if item[0] in modules]
    items = [item for item in items if item[0] in modules]
    items = update_path(items)
    return items

def is_empty(content):
    if content.strip() == '':
        return True
    without_comments = re.sub(r"""<!--.*?-->""", '', content, 0, re.DOTALL | re.MULTILINE)
    matches = re.match(r""".*?<\s*odoo\s*>\s*(<\s*data\s*>\s*)?\s*(<\s*/\s*data\s*>\s*)?<\s*/\s*odoo\s*>""", without_comments, re.DOTALL | re.MULTILINE)
    return bool(matches)

def remove_file_from_manifest(manifest_path, path):
    with open(manifest_path, 'r+') as file:
        content = ''.join(file.readlines())
        pattern = fr"""[\"']{path}[\"']\s*,?\s*"""
        new_content = re.sub(pattern, '', content, 1, re.DOTALL)
        pattern = r"""[\"']data[\"']\s*:\s*\[\s*]\s*,?"""
        new_content = re.sub(pattern, '', new_content, 0, re.DOTALL)
        file.seek(0)
        file.write(new_content)
        file.truncate()

def process(data):

    empties = set()

    for item in data:
        module, id, xmlid, _, filepath = item

        file = open(filepath, 'r+')

        content = ''.join(file.readlines())
        content = delete(id, xmlid, content)
        empty = is_empty(content)

        if empty:
            empties.add((filepath, module))


        file.seek(0)
        file.write(content)
        file.truncate()
        file.close()

    for empty_file, module in empties:
        os.unlink(empty_file)
        manifest_path = empty_file.split("/" + module + "/")[0] + "/" + module + "/__manifest__.py"
        remove_file_from_manifest(manifest_path, empty_file.split("/" + module + "/")[1])


def delete(id, xmlid, content):
    pattern = fr"""<\s*template\s+id\s*=\s*.({id}|{xmlid})..*?<\s*/\s*template\s*>\s*"""
    return re.sub(pattern, '', content, 0, re.DOTALL)

if __name__ == '__main__':
    modules = sys.argv[1].split(',')
    data = get_data(modules)

    process(data)
