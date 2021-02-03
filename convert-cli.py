from lxml import etree
from io import StringIO, BytesIO
import itertools
import re
import pickle
import os
import glob
import sys

xpath_predicats = [
    """contains(@id, "assets")""",
    """contains(@id, "qunit_suite")"""
]

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
    visited_manifests = []
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
                request = f"""//template"""
                templates = tree.xpath(request)

                for template in templates:
                    id = template.get("id")
                    inherits_from = None
                    if "inherit_id" in template.keys():
                        inherits_from = template.get("inherit_id")
                    if (id, inherits_from) not in [(ids, inherit_id) for _, ids, inherit_id, _ in items]:
                        continue
                    inherits_from = id
                    raw_actions = process(inherits_from, template, None, None, 0)
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
                    sorted_actions = sort_actions(actions)
                    for action in sorted_actions:
                        action_str = generate_action_str(action)
                        actions_str.append(action_str)

                    if not done[module]:
                        write_in_manifest(manifest_path, top)
                        done[module] = True

                    write_in_manifest(manifest_path, f"""\n{tabulation(2)}'{inherits_from}': [\n""")

                    full_str_content = '\n'.join(actions_str)

                    write_in_manifest(manifest_path, full_str_content)

                    write_in_manifest(manifest_path, "\n" + tabulation(2) + "],")

                    name = "tests/" + filename.replace("..", ".") + "/" + inherits_from + ".asset"
                    os.makedirs(os.path.dirname(name), exist_ok=True)

                    with open(name, "w") as f:
                        f.write(full_str_content)

                    visited_manifests.append(manifest_path)

    for path in list(set(visited_manifests)):
        write_in_manifest(path, "\n" + tabulation(1) +"}")


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
    'before': 'append'
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

    elif "add" in action[0]:
        content = f"""'{raw_content}',"""

    elif action[0] in methods:
        content = f"""('{methods[action[0]]}', '{raw_content}'),"""

    else:
        alert(('No string fo this case!', action))

    return '\n'.join([tabulation(3) + comment, tabulation(3) + content])


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
            return ('add', "# That shouldn't exist...", data['expr'], data['position'])
        s = data['expr'].replace("'", "").replace('"', "")
        path = re.search("""@.*=(?P<path>.*)]""", s).groupdict()['path']
        return (data['position'], path, data['expr'], data['position'])

    elif data['expr'] == None and data['position'] == None:
        return ('add', data[attr[file_type]], "", "new module")

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

def process(inherits_from, node, expr, position, depth):

    if depth > 2:
        print("---------------------------------")
        print("ATTENTION depth is getting bigger", inherits_from, *node.items(), expr, position, depth)
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
        values = process(inherits_from, n, expr, position, depth)
        res.append(values)

    return res

def get_data(modules):
    with open('results.pickle', 'rb') as handle:
        items = pickle.load(handle)
    items = [item for item in items if item[0] in modules]
    return items


if __name__ == '__main__':

    modules = sys.argv[1].split(',')
    items = get_data(modules)
    print(items)

    modules = [module for module, _, _, _ in items]
    convert(modules, items, "../community/addons/**", 3)
    convert(modules, items, "../enterprise/**", 2)


