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
                split_position = module_name_position_on_split
                if 'odoo/addons' in filename:
                    split_position += 1
                module = filename.split("/")[split_position]
                ids_accepted = process(filename, module)
                all += ids_accepted
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
        id = (module_name, template.get("id"), template.get("inherit_id", None), filename)
        is_valid = valid(template, [])
        if is_valid:
            ids.append(id)

    return ids

accepted_tags = ['script', 'link', 'xpath', 't-call']

def valid(node, tags):

    value = True

    for n in node.getchildren():

        tag = n.tag

        if tag == 't':
            if 't-call' in n.keys():
                tag = 't-call'
            if 't-call-assets' in n.keys():
                tag = 't-call-assets'


        if tag not in accepted_tags:
            return False

        if 'expr' in n.keys() and n.get("expr").startswith("//t[@t-set='head']"):
            return False

        if tag not in tags:
            tags.append(tag)

        value = value and valid(n, tags)

    if 'script' not in tags and 'link' not in tags:
        return False

    return value


if __name__ == "__main__":
    names = get_names("../community/**", 3)
    names += get_names("../enterprise/**", 2)

    print(len(names))

    with open('results.pickle', 'wb') as handle:
        pickle.dump(names, handle, protocol=pickle.HIGHEST_PROTOCOL)
