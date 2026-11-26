import json
nb=json.load(open('research/nb1119/santa-2026-the-elf-calculator-x-ray/santa-2026-the-elf-calculator-x-ray.ipynb',encoding='utf-8'))
txt='\n'.join(''.join(c.get('source','')) for c in nb['cells'])
i=txt.find('scored_0082'); print(txt[i-1500:i+400])
