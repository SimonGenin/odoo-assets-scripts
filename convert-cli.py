from lxml import etree
from io import StringIO, BytesIO
import itertools
import re
import pickle
import os
import glob
import sys
import secrets

xpath_predicats = [
    """contains(@id, "assets")""",
    """contains(@id, "qunit_suite")"""
]
#
template_ir_asset = """
            <record id="__id__" model="ir.asset">
                <field name="name">__name__</field>
                <field name="bundle">__bundle__</field>
                <field name="directive">__directive__</field>
                <field name="glob">__glob__</field>
                <field name="target" eval="__target__"></field>
                <field name="active" eval="__active__"></field>
                <field name="sequence" eval="__sequence__"></field>
            </record>
"""

names_changes = {
    "web.assets_tests": "web.test_tours"
}

def tabulation(n):
    return "    " * n

def convert_to_new_name(name):
    return name
    # if name in names_changes:
    #     return names_changes[name]
    # return name.replace('assets_', '')

def alert(message):
    print("---------------------------------")
    print("ATTENTION ", message)
    print("---------------------------------")

def convert(modules, items, paths, module_name_position_on_split):
    top = f"\n{tabulation(1)}'assets': {{"
    done = {}
    contents_to_write = {}
    visited_manifests = []
    manifest_that_should_be_visited = []
    visited_ir_asset_data = []
    for filename in glob.glob(paths, recursive=True):
        if os.path.isfile(filename):  # filter dirs
            if '.xml' in filename:
                module = filename.split("/")[module_name_position_on_split]
                if module not in modules:
                    continue
                done[module] = done.get(module, False)
                manifest_path = filename.split(module + "/")[0] + module + '/' + '__manifest__.py'
                with open(filename, "r") as xml_file:
                    xml_content = xml_file.readlines()
                    if "version" in xml_content[0]:
                        xml_content = xml_content[1:]  # Remove the xml declaration line
                    xml_content = ''.join(xml_content)

                parser = etree.XMLParser(remove_comments=True)
                tree = etree.parse(StringIO(xml_content), parser=parser)
                # request = f"""//template|//data/inherit_id|//t/@inherit_id"""
                request = f"""//template"""
                templates = tree.xpath(request)

                for template in templates:
                    top_asset = None
                    id = template.get("id")

                    inherits_from = None
                    primary = False
                    primary_parent = None
                    if "inherit_id" in template.keys():
                        inherits_from = template.get("inherit_id")
                    values = [(ids, xmlid, inherit_id, highest_inherit, mode) for _, ids, xmlid, inherit_id, highest_inherit, mode, _ in items]
                    keep = False
                    for ids, xmlid, inherit_id, highest_inherit, mode in values:
                        if not ((id == ids or id == xmlid) and inherit_id == inherits_from):
                            keep = keep or False
                        else:

                            keep = True
                            top_asset = highest_inherit
                            primary = mode == 'primary'
                            if primary:
                                if inherit_id != xmlid:
                                    # this should be done in data cause we need the previous highest parent
                                    primary_parent = inherit_id
                                top_asset = xmlid

                    if not keep:
                        continue

                    if not inherits_from:
                        inherits_from = id

                    if not top_asset:
                        top_asset = inherits_from

                    # if top_asset.startswith('web.'):
                    #     parts = top_asset.split('.')
                    #     if len(parts) > 1:
                    #         top_asset = '.'.join(parts[1:])

                    raw_actions = process(template, None, None, 0)
                    active = True
                    priority = 16
                    if 'active' in template.keys():
                        raw_active_content = template.get('active').strip().lower()
                        if raw_active_content == "0" or raw_active_content == "false":
                            active = False
                    if 'priority' in template.keys():
                        raw_priority_content = template.get('priority').strip().lower()
                        priority = int(raw_priority_content)
                    # inherits_from = convert_to_new_name(inherits_from)
                    actions = []

                    cleaned_raw_actions = []
                    for raw_action in raw_actions:
                        while isinstance(raw_action, list) and len(raw_action) == 1:
                            raw_action = raw_action[0]
                        if isinstance(raw_action, list):
                            cleaned_raw_actions += raw_action
                        else:
                            cleaned_raw_actions.append(raw_action)

                    for raw_action in cleaned_raw_actions:
                        action = generate_action(raw_action)
                        actions.append(action)

                    actions_str = []
                    ir_asset_actions_str = []
                    sorted_actions = sort_actions(actions)
                    for action in sorted_actions:
                        if active == False or priority != 16:
                            ir_asset_actions_str.append(generate_ir_asset_action_str(action, active,priority, id, top_asset))
                        else:
                            action_str = generate_action_str(action)
                            actions_str.append(action_str)

                    if len(ir_asset_actions_str):
                        ir_asset_file_path = filename.split(module + "/")[0] + module + '/' + 'data/' + 'ir_asset.xml'
                        ir_asset_data_dir = filename.split(module + "/")[0] + module + '/' + 'data'
                        if not os.path.exists(ir_asset_data_dir):
                            os.makedirs(ir_asset_data_dir)
                        content = '\n'.join(ir_asset_actions_str)
                        visited_ir_asset_data.append(ir_asset_file_path)
                        with open(ir_asset_file_path, "a") as f:
                            f.write(content)

                    if not module in contents_to_write:
                        contents_to_write[module] = {}
                        contents_to_write[module]['manifest_path'] = manifest_path
                        contents_to_write[module]['assets'] = {}
                        contents_to_write[module]['was_assets_qweb_present'] = False

                    if top_asset not in contents_to_write[module]['assets'].keys():
                        contents_to_write[module]['assets'][top_asset] = []

                    if primary and primary_parent:
                        value = '\n'.join([tabulation(3) + "# Is primary with parent", tabulation(3) + f"('include', '{primary_parent}'),"])
                        actions_str.insert(0, value)


                    # todo
                    if top_asset == 'web.assets_qweb':
                        top_asset = 'web.assets_qweb'
                        contents_to_write[module]['was_assets_qweb_present'] = True
                        content = convert_qweb_key_to_asset(manifest_path)
                        if content:
                            contents_to_write[module]['assets'][top_asset].extend(format_qweb_conversion(content, module))

                    contents_to_write[module]['assets'][top_asset].extend(actions_str)

                    visited_manifests.append(manifest_path)

    for module_name, module_content in contents_to_write.items():
        manifest_path = module_content['manifest_path']
        sanitize_manifest(manifest_path)
        write_in_manifest(manifest_path, top)

        # todo
        if not module_content['was_assets_qweb_present']:
            content = convert_qweb_key_to_asset(manifest_path)
            if content:
                contents_to_write[module_name]['assets']['web.assets_qweb'] = format_qweb_conversion(content, module_name)


        for asset_name, asset_content in module_content['assets'].items():
            write_in_manifest(manifest_path, f"""\n{tabulation(2)}'{asset_name}': [\n""")
            full_str_content = '\n'.join(asset_content)
            write_in_manifest(manifest_path, full_str_content)
            write_in_manifest(manifest_path, "\n" + tabulation(2) + "],")

    for path in list(set(visited_manifests)):
        write_in_manifest(path, "\n" + tabulation(1) +"}")

    top = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
    """

    bottom = """
    </data>
</odoo>
    """

    for path in list(set(visited_ir_asset_data)):
        with open(path, 'r+') as f:
            content = f.read()
            f.seek(0)
            f.write(top + content + bottom)
            f.truncate()
        this_module_manifest_path = path.replace('data/ir_asset.xml', '__manifest__.py')
        with open(this_module_manifest_path, 'r+') as f:
            content = f.read()
            content = add_ir_asset_to_manifest_content(content)
            f.seek(0)
            f.write(content)
            f.truncate()

    return visited_manifests

def sanitize_manifest(path):
    write_in_manifest(path, ',')
    file = open(path, 'r+')
    content = file.read()
    content = re.sub(r""",\s*,""", ',', content, 0, re.DOTALL | re.MULTILINE)
    file.seek(0)
    file.write(content)
    file.truncate()
    file.close()

def add_ir_asset_to_manifest_content(content):
    result = re.search(r'''(?P<data>[\"']data[\"']\s*:\s*\[.*?]\s*,?)''', content, re.MULTILINE | re.DOTALL)
    if not result:
        print(">>> fuck there is no data key")
    result = re.search(r'''[\"']data[\"']\s*:\s*\[(?P<xmls>.*?)]\s*,?''', content, re.MULTILINE | re.DOTALL)
    new_data =  "\n" + tabulation(2) + "'data/ir_asset.xml'," + result['xmls'].rstrip() + '\n' + tabulation(1) + '],'
    return re.sub(r'''([\"']data[\"']\s*:\s*\[).*?]\s*,?''', rf"\1{new_data}", content, 0, re.MULTILINE | re.DOTALL)


def format_qweb_conversion(content, module):
    content = content.split(',')
    content = list(map(str.strip, content))
    content = filter(lambda x: x != "", content)
    content = list(map(lambda x: x[0] + module + "/" + x[1:] , content))
    content = list(map(lambda x: tabulation(3) + x + ",", content))
    return content

def convert_qweb_key_to_asset(manifest_path):
    f = open(manifest_path, "r+")
    content = f.read()
    pattern = r"""(?P<all>[\"']qweb[\"']\s*:\s*\[(?P<content>.*?)\]\s*,?\s*)"""
    matches = re.search(pattern, content, re.DOTALL)
    if matches:
        new_content = content.replace(matches['all'], '')
        f.seek(0)
        f.write(new_content)
        f.truncate()
        f.close()

        return matches['content']


def write_in_manifest(manifest_path, content):
    with open(manifest_path, "r+") as f:
        position = 0
        char = None
        while char != '}':
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - position, os.SEEK_SET)
            char = f.read(1)
            position += 1
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - position, os.SEEK_SET)
        f.write(content)
        f.write('\n}\n')

methods = {
    'replace': 'replace',
    'remove': 'remove',
    'include': 'include',
    'append': 'append',
    'before': 'before',
    'add_end': 'append',
    'add_after': 'after',
}

def generate_action_str(action):

    comment = f"""# {action[3]} {action[2]}"""


    raw_content = action[1]

    if raw_content.startswith("/"):
        raw_content = action[1][1:]

    content = None

    if "unsafe" in action[0]:
        content = "# wtf"

    elif "no-content" in action[0]:
        content = "# There is no content in this asset..."

    elif "t-call-assets" in action[0]:
        content = "# t-call-assets needs supervision"

    elif "raw" in action[0]:
        content = "# raw need to be manually included"

    elif "add_end" in action[0] or "add" == action[0] :
        content = f"""'{raw_content}',"""

    elif "before" in action[0] and (action[2] == "//link" or action[2] == "//script"):
        content = f"""('prepend', '{raw_content}'),"""

    elif "replace" in action[0] or "add_after" in action[0] or "before" in action[0]:
        expr = action[2]
        pattern = r"""[\"'](?P<path>.+(\.js|\.scss|\.css))[\"']"""
        if "@t-call" in expr:
            pattern = r"""[\"'](?P<path>.+)[\"']"""
        matches = re.search(pattern, expr, re.DOTALL)
        if not matches:
            content = "# unsafe... " + ' '.join(action)
            return content
        target = matches['path']
        if target.startswith('/'):
            target = target[1:]
        content = f"""('{methods[action[0]]}', '{target}', '{raw_content}'),"""

    elif action[0] in methods:
        content = f"""('{methods[action[0]]}', '{raw_content}'),"""

    else:
        alert(('No string fo this case!', action))

    return '\n'.join([tabulation(3) + comment, tabulation(3) + content])

def generate_ir_asset_action_str(action, active, priority, template_id, template_inherits_from):

    raw_content = action[1]
    if raw_content.startswith("/"):
        raw_content = action[1][1:]

    id = template_id
    directive = methods.get(action[0], action[0])
    bundle = template_inherits_from
    name = template_id.replace("_", " ")
    glob = raw_content
    target = "None"

    if directive == "before" and (action[2] == "//link" or action[2] == "//script"):
        directive = "prepend"

    if "replace" in directive or "before" in directive or "after" in directive:
        expr = action[2]
        pattern = r"""[\"'](?P<path>.+(\.js|\.scss|\.css))[\"']"""
        if "@t-call" in expr:
            pattern = r"""[\"'](?P<path>.+)[\"']"""
        matches = re.search(pattern, expr, re.DOTALL)
        target = matches['path']
        if target.startswith('/'):
            target = target[1:]

    secret = secrets.token_hex(nbytes=1)
    instance = template_ir_asset.replace("__id__", id + "_" + secret).replace("__name__", name).replace('__bundle__', bundle)
    instance = instance.replace('__directive__', directive).replace('__glob__', glob).replace('__target__', target)
    instance = instance.replace("__active__", str(active)).replace("__sequence__", str(priority))

    return instance


def sort_actions(actions):
    after = []
    end = []
    other = []
    for action in actions:
        if 'end' in action[0]:
            end.append(action)
        elif 'after' in action[0]:
            after.append(action)
        else:
            other.append(action)
    return other + after + end

attr = {
    'js': 'src',
    'scss': 'href'
}

def generate_action(data):

    file_type = infer_file_type(data)

    if file_type == "unsafe":
        return ('unsafe', "", data['expr'], data['position'])

    elif file_type == "template":
        return ('no-content', "", data['expr'], data['position'])

    elif file_type == 't-tag' and data.get('t-call'):
        return ('include', data['t-call'], data['expr'], data['position'])

    elif file_type == 't-tag' and data.get('t-raw'):
        return ('raw', data['t-raw'], data['expr'], data['position'])

    elif file_type == 't-tag' and data.get('t-call-assets'):
        alert(("T CALL ASSETS", data))
        return ('t-call-assets', data['t-call-assets'], data['expr'], data['position'])

    elif file_type == 't-tag':
        return ('unsafe', "", data['expr'], data['position'])

    elif data['tag'] == 'xpath':
        if data['expr'] == '.' and data['position'] == 'inside':
            return ('unsafe', "", data['expr'], data['position'])
        s = data['expr'].replace("'", "").replace('"', "")
        path = re.search("""@.*=(?P<path>.*)]""", s).groupdict()['path']
        return (data['position'], path, data['expr'], data['position'])

    elif data['expr'] == None and data['position'] == None:
        return ('add', data[attr[file_type]], "", "new asset template")

    elif data['expr'] == '.' and data['position'] == 'inside':
        return ('add', data[attr[file_type]], data['expr'], data['position'])

    # maybe I can wait to add them at the end ?
    elif 'last()' in data["expr"] and data['position'] == 'after':
        return ('add_end', data[attr[file_type]], data['expr'], data['position'])

    elif data['position'] == 'after':
        return ('add_after', data[attr[file_type]], data['expr'], data['position'])

    elif data['position'] == 'before':
        return ('before', data[attr[file_type]], data['expr'], data['position'])

    elif data['position'] == 'replace':
        return ('replace', data[attr[file_type]], data['expr'], data['position'])

    else:
        alert(("Nothing could be done...", data))
        return ('unsafe', "", data['expr'], data['position'])

def infer_file_type(data):

    if data['tag'] == 'script':
        return 'js'

    if data['tag'] == 'template':
        return 'template'

    if data['tag'] == 'link':
        return 'scss'

    if data["tag"] == "t":
        return 't-tag'

    if data["tag"] == "xpath":
        return 'xpath'

    alert(("unknown type:", data))
    return 'unsafe'

def process(node, expr, position, depth, active=True):

    if depth > 2:
        print("---------------------------------")
        print("ATTENTION depth is getting bigger", *node.items(), expr, position, depth)
        print("---------------------------------")

    depth += 1

    if not len(node.getchildren()):
        if node.tag == "xpath":
            expr = node.get("expr")
            position = node.get("position")
        if depth == 1:
            return [dict((*node.items(), ('tag', node.tag), ('expr', expr), ('position', position), ('depth', depth)))]
        return dict((*node.items(), ('tag', node.tag), ('expr', expr), ('position', position), ('depth', depth)))


    if node.tag == "xpath":
        expr = node.get("expr")
        position = node.get("position") # should we default to inside if nothing ?

    res = []

    for n in node.getchildren():

        if (n.tag == 'script' or n.tag == 'link') and n.text:
            alert(("There is a raw text in assets", n.text))
            continue
        values = process(n, expr, position, depth, active)
        res.append(values)

    return res

def get_data(modules):
    with open('results.pickle', 'rb') as handle:
        items = pickle.load(handle)
    items = [item for item in items if item[0] in modules]
    return items


def get_all_manifests(modules, path, module_name_position_on_split):
    acc = []
    for filename in glob.glob(path, recursive=True):
        if os.path.isfile(filename):  # filter dirs
            if '__manifest__.py' in filename:
                module = filename.split("/")[module_name_position_on_split]
                if module not in modules:
                    continue
                acc.append(filename)
    return acc

def has_qweb_key_and_not_empty(manifest_path):

    with open(manifest_path, 'r') as f:
        content = f.read()

    has_key_pattern = r"""['"]qweb['"]\s*:"""
    key_is_empty = r"""['"]qweb['"]\s*:\s*\[\s*\]"""

    if re.search(key_is_empty, content, re.DOTALL):
        return False

    if re.search(has_key_pattern, content, re.DOTALL):
        return True

    return False

if __name__ == '__main__':

    m = sys.argv[1].split(',')
    items = get_data(m)

    modules = [module for module, _, _, _, _, _, _ in items]
    visited_manifests = convert(modules, items, "../community/addons/**", 3)
    print('./community/addons/** done')
    visited_manifests += convert(modules, items, "../community/odoo/addons/**", 4)
    print('./community/odoo/addons/** done')
    visited_manifests += convert(modules, items, "../enterprise/**", 2)
    print('./enterprise/** done')


    manifests = get_all_manifests(m, "../community/addons/**", 3)
    manifests += get_all_manifests(m, "../community/odoo/addons/**", 4)
    manifests += get_all_manifests(m, "../enterprise/**", 2)

    visited_manifests = list(set(visited_manifests))
    manifests = list(set(manifests))

    for path in visited_manifests:
        manifests.remove(path)

    for manifest in manifests:
        if has_qweb_key_and_not_empty(manifest):
            sanitize_manifest(manifest)
            write_in_manifest(manifest, f"\n{tabulation(1)}'assets': {{")
            content = convert_qweb_key_to_asset(manifest)
            module = manifest.split("/")[3 if 'community/addons/' in manifest else 2]
            contents = format_qweb_conversion(content, module)
            write_in_manifest(manifest, f"""\n{tabulation(2)}'web.assets_qweb': [\n""")
            full_str_content = '\n'.join(contents)
            write_in_manifest(manifest, full_str_content)
            write_in_manifest(manifest, "\n" + tabulation(2) + "],")
            write_in_manifest(manifest, "\n" + tabulation(1) + "}")

