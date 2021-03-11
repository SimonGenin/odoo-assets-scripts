import os
import ast
import glob

def get_manifest_dict(mp):
    file = open(mp, "r")
    contents = file.read()
    dictionary = ast.literal_eval(contents)
    file.close()
    return dictionary

if __name__ == '__main__':
    module_paths = [
        '../community/addons',
        '../community/odoo/addons',
        '../enterprise',
    ]

    manifest_paths = []

    for module_path in module_paths:
        dirs = next(os.walk(module_path))[1]
        for d in dirs:
            manifest_path = module_path + '/' + d + '/__manifest__.py'
            if not os.path.exists(manifest_path):
                continue
            manifest_paths.append(manifest_path)

    for manifest_path in manifest_paths:
        manifest = get_manifest_dict(manifest_path)

        if 'qweb' in manifest:
            bundle_path = manifest_path.replace('__manifest__.py', '')
            for qweb in manifest['qweb']:
                res = glob.glob(bundle_path + qweb)
                if not res:
                    print("Not yet converted:", qweb, 'in', manifest_path)

        if 'assets' in manifest:
            bundle_path = manifest_path.replace('/__manifest__.py', '')
            module = bundle_path.split("/")[-1]
            bundle_path = bundle_path.replace(module, "")
            for asset in manifest['assets'].keys():
                asset_content = manifest['assets'][asset]
                for asset_line in asset_content:
                    if type(asset_line) == tuple:
                        if asset_line[0] == 'include':
                            continue
                        asset_line = asset_line[-1]
                    path = bundle_path + asset_line
                    res = glob.glob(path)
                    if 'base' in path:
                        path = path.replace("community/addons", "community/odoo/addons")
                    if module == 'web_enterprise' and 'web/' in path:
                        path = path.replace("enterprise", "community/addons")
                    if not res:
                        path = path.replace("/**/*", "/*")
                        res = glob.glob(path)
                        if not res:
                            if asset_line.startswith("http"):
                                continue
                            print("Already converted:", asset_line, 'in', manifest_path)

