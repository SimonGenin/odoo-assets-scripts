import pickle
import re

def get_data():
    with open('results.pickle', 'rb') as handle:
        items = pickle.load(handle)
    return items

def process(data):

    handles = {}

    for item in data:
        _, id, _, filepath = item

        if filepath not in handles.keys():
            handles[filepath] = open(filepath, "r+")

        file = handles[filepath]

        content = ''.join(file.readlines())
        content = delete(id, content)

        is_empty = content

        file.write(content)

    for key, handle in handles.items():
        handle.close()

def delete(id, content):
    pattern = fr"""<\s*template\s+id\s*=\s*.{id}..*?<\s*/\s*template\s*>"""
    return re.sub(pattern, '', content, 0, re.DOTALL)

if __name__ == '__main__':
    data = get_data()
    process(data)
