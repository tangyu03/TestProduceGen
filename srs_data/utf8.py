import ast
src = open('srs_data/pt_srs.py', encoding='utf-8').read()
calls = [n for n in ast.walk(ast.parse(src))
         if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'add_br']
calls.sort(key=lambda n: n.lineno)
for i, n in enumerate(calls, 1):
    kw = {k.arg: k for k in n.keywords}
    inv = ast.literal_eval(kw['entities_involved'].value)
    if len(inv) > 1 and 'constrained_entity' not in kw:
        print(f'BR-{i:03d} = bid {ast.literal_eval(kw["bid"].value)} '
              f'(line {n.lineno}) involved={inv}  <- 缺 constrained_entity')
