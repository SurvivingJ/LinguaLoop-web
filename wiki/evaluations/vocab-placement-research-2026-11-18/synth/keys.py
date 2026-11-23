import json,sys
d=json.load(open(sys.argv[1]))
r=d['rows'][0]
print(r.keys())
s=r['res']['D3S']
print([x['n'] for x in s])
print(s[-1])
