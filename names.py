import glob, os
from lxml import etree
from io import StringIO, BytesIO
import itertools
import re
import pickle

def get_names(path, module_name_position_on_split):
    all = []
    for filename in glob.iglob(path, recursive=True):
        if os.path.isfile(filename):  # filter dirs
            if filename.endswith(".xml") and 'l10n_' not in filename:
                module = filename.split("/")[module_name_position_on_split]
                get_all_ids = process(filename, module)
                all += get_all_ids
    return all

def process(filename, module_name):

    ids = []

    with open(filename, "r") as xml_file:
        xml_content = xml_file.readlines()
        if "version" in xml_content[0]:
            xml_content = xml_content[1:]  # Remove the xml declaration line
        xml_content = ''.join(xml_content)

    tree = etree.parse(StringIO(xml_content))
    request = f"""//template"""
    templates = tree.xpath(request)

    for template in templates:
        id = template.get("id")
        if id == None:
            continue
        inherit_id = template.get("inherit_id")
        t_call_assets, t_calls = get_t_calls(template, [], [])
        ids.append( { 'module' : module_name, 'id' : id, 'inherit_id' :inherit_id, 't-call-assets': t_call_assets, 't-call': t_calls })

    return ids


def get_t_calls(node, t_call_assets, t_call):

    for n in node.getchildren():

        if n.tag == 't' and 't-call-assets' in n.keys():
            t_call_assets.append(n.get('t-call-assets'))

        if n.tag == 't' and 't-call' in n.keys():
            t_call.append(n.get('t-call'))

        get_t_calls(n, t_call_assets, t_call)

    return t_call_assets, t_call


def add_inherits(source, data):
    acc = []
    for asset in source:
        for element in data:
            if asset['id'] == element['inherit_id'] and element not in source:
                acc.append(element)
            if asset['inherit_id'] == element['id'] and element not in source:
                acc.append(element)
            if asset['module'] + "." + asset['id'] == element['inherit_id'] and element not in source:
                acc.append(element)
            if asset['inherit_id'] == element['module'] + "." + element['id'] and element not in source:
                acc.append(element)
    return acc

if __name__ == "__main__":
    data = get_names("../community/**", 3)
    data += get_names("../enterprise/**", 2)


    with open('assets.pickle', 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    has_t_call_assets = [element for element in data if element['t-call-assets']]
    assets_for_certain = []
    for element in data:
        for to_add in has_t_call_assets:
            if element['id'] == to_add['inherit_id']:
                assets_for_certain.append(to_add)
            if element['module'] + "." + element['id'] == to_add['inherit_id']:
                assets_for_certain.append(to_add)
    print(assets_for_certain)

    size = len(assets_for_certain)
    stop = False

    while not stop:
        news = add_inherits(assets_for_certain, data)
        print(news)
        for x in news:
            assets_for_certain.append(x)
        new_size = len(assets_for_certain)
        print(new_size)
        if size == new_size:
            stop = True
        size = new_size
    print(assets_for_certain)

    has_t_call = [element for element in data if element['t-call']]

