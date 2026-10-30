import json, re, sys
def load(path):
    raw = open(path, encoding='utf-8').read()
    try:
        obj = json.loads(raw)
        txt = obj['result'] if isinstance(obj, dict) else obj[0]['text']
    except Exception:
        txt = raw
    if txt.startswith('{"result"'):
        txt = json.loads(txt)['result']
    m = re.search(r'\n\n<untrusted-data-[^>]+>\n(.*)\n</untrusted-data', txt, re.S)
    return json.loads(m.group(1))
if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2:]
    rows = load(src)[0]
    for k, v in rows.items():
        dest = out.pop(0) if out else k
        if isinstance(v, str): v = json.loads(v)
        json.dump(v or [], open(f'/home/user/LinguaLoop-web/scratch_offline/snap/{dest}.json', 'w'), ensure_ascii=False)
        print(dest, len(v or []))
