import json,pathlib,sys
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/work')
base=root/'baseline';candidate=root/'candidate';results=[]
def differences(a,b,path=''):
    if type(a)!=type(b):return [path]
    if isinstance(a,dict):
        r=[]
        for key in sorted(a.keys()|b.keys()):
            if key not in a or key not in b:r.append(path+'/'+key)
            else:r.extend(differences(a[key],b[key],path+'/'+key))
        return r
    if isinstance(a,list):
        if len(a)!=len(b):return [path+'/length']
        return [p for i,(x,y) in enumerate(zip(a,b)) for p in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [path]
for filename in sorted(p.name for p in base.glob('*.json') if p.name not in {'summary.json','versions.json','server_info.json'}):
    b=json.loads((base/filename).read_text());c=json.loads((candidate/filename).read_text())
    result={'case':b['name'],'baseline_pass':b['passed'],'candidate_pass':c['passed'],'same_request':b['request']==c['request'],'same_text':b.get('text')==c.get('text'),'same_canonical_response':b.get('canonical')==c.get('canonical'),'differences':differences(b.get('canonical'),c.get('canonical'))}
    results.append(result)
summary={'cases':results,'passed_baseline':sum(r['baseline_pass'] for r in results),'passed_candidate':sum(r['candidate_pass'] for r in results),'identical_requests':sum(r['same_request'] for r in results),'identical_text':sum(r['same_text'] for r in results),'identical_canonical_response':sum(r['same_canonical_response'] for r in results)}
(root/'comparison.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
