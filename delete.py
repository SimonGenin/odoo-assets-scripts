import pickle
import re
import os

def get_data():
    with open('results.pickle', 'rb') as handle:
        items = pickle.load(handle)
    return items

def is_empty(content):
    if content.strip() == '':
        return True
    matches = re.match(r""".*?<\s*odoo\s*>\s*(<\s*data\s*>\s*)?\s*(<\s*/\s*data\s*>\s*)?<\s*/\s*odoo\s*>""", content, re.DOTALL | re.MULTILINE)
    return bool(matches)

def remove_file_from_manifest(manifest_path, path):
    with open(manifest_path, 'r+') as file:
        content = ''.join(file.readlines())
        pattern = fr""".{path[1:]}.\s*,?"""
        new_content = re.sub(pattern, '', content, 1, re.DOTALL)
        pattern = r"""[\"']data[\"']\s*:\s*\[\s*]\s*,?"""
        new_content = re.sub(pattern, '', new_content, 0, re.DOTALL)
        file.seek(0)
        file.write(new_content)
        file.truncate()

def process(data):

    empties = set()

    for item in data:
        module, id, _, filepath = item

        file = open(filepath, 'r+')

        content = ''.join(file.readlines())
        content = delete(id, content)
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


def delete(id, content):
    pattern = fr"""<\s*template\s+id\s*=\s*.{id}..*?<\s*/\s*template\s*>"""
    return re.sub(pattern, '', content, 0, re.DOTALL)

if __name__ == '__main__':
    data = get_data()
    process(data)
