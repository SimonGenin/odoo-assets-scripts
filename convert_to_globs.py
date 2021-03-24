import os
import re
import ast
import glob
from functools import cmp_to_key


def assets_in_manifest(mp):
    with open(mp, 'r') as f:
        content = f.read()
    pattern = r"""[\"']assets[\"']\s*:"""
    match = re.search(pattern, content, re.DOTALL)
    return bool(match)

def get_manifest_dict(mp):
    file = open(mp, "r")
    contents = file.read()
    dictionary = ast.literal_eval(contents)
    file.close()
    return dictionary

def check_if_equal(list_1, list_2):
    """ Check if both the lists are of same length and if yes then compare
    sorted versions of both the list to check if both of them are equal
    i.e. contain similar elements with same frequency. """
    if len(list_1) != len(list_2):
        return False
    return sorted(list_1) == sorted(list_2)

def by_deepest_path(x, y):
    x_length = len(x.split('/'))
    y_length = len(y.split('/'))
    return  x_length - y_length

def process(module_path, actions):

    for action in actions:
        if type(action) == tuple:
            return actions, False

    all_paths = glob.glob(module_path + "**/*", recursive=True)
    all_dirs = filter(lambda path: os.path.isdir(path), all_paths)
    all_dirs = sorted(all_dirs, key=cmp_to_key(by_deepest_path))

    for dir in all_dirs:
        _glob = dir + "/**/*"
        paths = glob.glob(_glob, recursive=True)
        all_files = list(filter(lambda path: os.path.isfile(path), paths))
        all_files = list(map(lambda p: p.replace("../enterprise/", "").replace("../community/addons/", ""), all_files))
        if check_if_equal(actions, all_files):
            return [_glob.replace("../enterprise/", "").replace("../community/addons/", "")], True

    return actions, False

def tabulation(n):
    return "    " * n

if __name__ == '__main__':

    ignore = [
        'web', 'web_editor', 'web_enterprise'
    ]

    module_paths = [
        '../community/addons',
        '../enterprise',
    ]

    manifest_paths = []

    for module_path in module_paths:
        dirs = next(os.walk(module_path))[1]
        for d in dirs:
            if d in ignore:
                print(d, "is ignored.")
                continue
            manifest_path = module_path + '/' + d + '/__manifest__.py'
            if 'test_assetsbundle' in manifest_path:
                continue
            # if 'i18n' in manifest_path:
            #     continue
            if not os.path.exists(manifest_path):
                continue
            if assets_in_manifest(manifest_path):
                manifest_paths.append(manifest_path)

    # manifest_paths = ['../enterprise/helpdesk/__manifest__.py']

    for manifest_path in manifest_paths:
        manifest = get_manifest_dict(manifest_path)
        for asset in manifest['assets'].keys():
            asset_content = manifest['assets'][asset]
            new_content, success = process(manifest_path.replace("__manifest__.py", ""), manifest['assets'][asset])
            new_content = list(map(lambda path: "'" + path + "'" if type(path) != tuple else str(path), new_content))
            if not len(new_content):
                print(manifest_path, asset)
                str_content = ""
            else:
                formatted_content = list(map(lambda path: tabulation(3) + path + ",", new_content[1:]))
                formatted_content.insert(0, new_content[0] + ',')
                str_content = '\n'.join(formatted_content)
            pattern = rf"""(['"]{asset}['"]\s*:\s*\[\s*).*?(\s*\],)"""
            with open(manifest_path, "r+") as file:
                contents = file.read()
                res = re.sub(pattern, rf'\1{str_content}\2', contents, 0, re.DOTALL)
                file.seek(0)
                file.write(res)
                file.truncate()

