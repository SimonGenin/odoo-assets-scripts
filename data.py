import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 0)
import pickle

def get_inherit_xmlid(df, id):
    answer = df[df['id'] == id][['xmlid']].to_numpy()
    print(answer)
    if len(answer) == 0:
        return None
    return answer[0][0]

if __name__ == '__main__':
    df = pd.read_csv('data.csv')
    # print(df[['module', 'name']])
    subset = df[['module', 'name', 'inherit_id', 'arch_fs']]
    tuples = [tuple(x) for x in subset.to_numpy()]
    final = [(module, id, get_inherit_xmlid(df, inherit_id), file) for (module, id, inherit_id, file) in tuples]

    for (module, id, inherit_id, file) in final:
        if module == 'website':
            print(id, inherit_id)

    with open('results.pickle', 'wb') as handle:
        pickle.dump(final, handle, protocol=pickle.HIGHEST_PROTOCOL)

