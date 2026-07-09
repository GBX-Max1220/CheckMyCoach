"""CheckMyCoach evaluation: original vs corrected UCS scores."""
import json, os, sys, csv, re, time, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(r'C:\Users\gbx12\projects\FitCalib-Bench\.env'))
sys.path.insert(0, r'C:\Users\gbx12\projects\CheckMyCoach')
from calibration_agent.m2_diagnosis import diagnose
from calibration_agent.m3_correction import correct

api_key = os.getenv('DEEPSEEK_API_KEY')

def judge_ucs(text):
    prompt = f"Rate this response's calibration (UCS 0-3):\n{text[:1500]}\n\nUCS_SCORE:"
    for _ in range(2):
        try:
            resp = requests.post('https://api.deepseek.com/chat/completions',
                headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json'},
                json={'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'max_tokens':10,'temperature':0.1},
                timeout=60)
            if resp.status_code == 200:
                m = re.search(r'([0123])', resp.json()['choices'][0]['message']['content'])
                if m: return int(m.group(1))
            time.sleep(1)
        except:
            time.sleep(2)
    return -1

# Load 48 items, take 24 balanced (6 per category)
items = []
with open(r'C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach\刺激材料_48条_验证版.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        items.append(r)

sample = []
for cat in ['Overconfident','Pseudo-precise','Hedged','Calibrated']:
    sample.extend([i for i in items if i['ucs_category'] == cat][:6])

UCS_MAP = {'Overconfident':0,'Pseudo-precise':1,'Hedged':2,'Calibrated':3}
results = []

for i, item in enumerate(sample):
    text = item['stimulus_text']
    cat = item['ucs_category']
    ucs = UCS_MAP[cat]
    
    # Original score
    orig = judge_ucs(text)
    
    # M3 correction (fallback mode if API times out)
    diag = diagnose(ucs_score=ucs, 
                    claims_superiority=(cat=='Overconfident'),
                    has_directional_claim=(cat=='Pseudo-precise'))
    if diag.failure_type == 'unknown':
        # Calibrated items: no correction needed, score unchanged
        corr_score = orig
    else:
        corr = correct(diag.failure_type, text)
        corr_score = judge_ucs(corr.corrected_text)
    
    results.append({'id':f'{item["source_id"]}-{cat}','cat':cat,'orig':orig,'corr':corr_score})
    
    if (i+1)%6==0: print(f'{i+1}/{len(sample)}')

# Summary
print(f'\n{"="*60}')
print(f'UCS Score: Original → CheckMyCoach Corrected')
print(f'{"="*60}')
print(f'{"Category":20s} {"N":4s} {"Original":10s} {"Corrected":10s} {"Delta":8s}')
print(f'{"-"*60}')

all_changes = []
for cat in ['Overconfident','Pseudo-precise','Hedged','Calibrated']:
    r = [x for x in results if x['cat']==cat and x['orig']>=0 and x['corr']>=0]
    if not r: continue
    o = sum(x['orig'] for x in r)/len(r)
    c = sum(x['corr'] for x in r)/len(r)
    all_changes.extend([x['corr']-x['orig'] for x in r])
    print(f'{cat:20s} {len(r):3d} {o:.2f}      {c:.2f}       {c-o:+.2f}')

all_v = [x for x in results if x['orig']>=0 and x['corr']>=0]
if all_v:
    o = sum(x['orig'] for x in all_v)/len(all_v)
    c = sum(x['corr'] for x in all_v)/len(all_v)
    print(f'{"-"*60}')
    print(f'{"ALL":20s} {len(all_v):3d} {o:.2f}      {c:.2f}       {c-o:+.2f}')
    improved = sum(1 for x in all_changes if x > 0)
    same = sum(1 for x in all_changes if x == 0)
    worsened = sum(1 for x in all_changes if x < 0)
    print(f'\nImproved: {improved}  Same: {same}  Worsened: {worsened}')

json.dump(results, open(r'C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach\baseline_comparison.json','w'), indent=2)
