import json
import pysd

def transform_pycase(file:str):
    with open('domains_old.json', 'r') as x:
        new = {}
        data = json.load(x)
        for d, l in data.items():
            new[d] = [e.replace(' ','_').lower() for e in l]
        with open('domains.json', 'w') as y:
            json.dump(new, y)

model = pysd.load('model.py')
doc_df = model.doc
#print(doc_df.iloc[0])

doc_doc_df = doc_df.dropna(subset='Comment')
for _, e in doc_doc_df.iterrows():
    if e['Comment']:
        print(e['Comment'])