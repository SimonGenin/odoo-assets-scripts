import os
import re
from os import path

def assets_in_manifest(mp):
    with open(mp, 'r') as f:
        content = f.read()
    pattern = r"""[\"']assets[\"']\s*:"""
    match = re.search(pattern, content, re.DOTALL)
    return bool(match)

def ir_asset_xml(module_path):
    return path.exists(module_path + '/data/ir_asset.xml')

if __name__ == '__main__':

    module_paths = [
        '../community/addons',
        '../enterprise',
        '../community/odoo/addons'
    ]

    keep = []

    for module_path in module_paths:
        dirs = next(os.walk(module_path))[1]
        for d in dirs:
            manifest_path = module_path + '/' + d + '/__manifest__.py'

            # if 'l10n' in d:
            #     print(d, "is for translation, we pass")
            #     continue

            if not path.exists(manifest_path):
                print(d, "is weird, let's pass...")
                continue

            if not assets_in_manifest(manifest_path) and not ir_asset_xml(module_path):
                keep.append(d)
                print(d, 'added')
            else:
                print(d, 'has been done already (or had nothing to be done)')

    print(' && '.join(sorted(map(lambda x: 'assets ' + x, keep))))
