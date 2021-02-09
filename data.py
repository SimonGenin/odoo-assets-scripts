import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 0)
import pickle
import math

def get_xmlid(df, id):
    answer = df[df['id'] == id][['xmlid']].to_numpy()
    if len(answer) == 0:
        return None
    return answer[0][0]

def get_parent_id(df, id):
    answer = df[df['id'] == id][['id', 'inherit_id']].to_numpy()
    if len(answer) == 0:
        return None
    return answer[0][0], answer[0][1]

def get_highest_inherit_id(df, id):
    current_toppest_id = None
    current_toppest_to_try = id
    while True:

        id_of_parent = get_parent_id(df, current_toppest_to_try)

        if id_of_parent == None:
            return current_toppest_id

        current_toppest_id = id_of_parent[0]

        if math.isnan(id_of_parent[1]):
            return current_toppest_id

        current_toppest_to_try = id_of_parent[1]


if __name__ == '__main__':
    df = pd.read_csv('data.csv')
    # print(df[['module', 'name']])
    subset = df[['module', 'name', 'xmlid', 'inherit_id', 'arch_fs']]
    tuples = [tuple(x) for x in subset.to_numpy()]

    final = [(module, id, xmlid, get_xmlid(df, inherit_id), get_xmlid(df, get_highest_inherit_id(df, inherit_id)), file) for (module, id, xmlid, inherit_id, file) in tuples]

    with open('results.pickle', 'wb') as handle:
        pickle.dump(final, handle, protocol=pickle.HIGHEST_PROTOCOL)

