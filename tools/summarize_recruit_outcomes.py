# Per-class summary tables of data/recruiting/recruit_outcomes.csv (Phase 9 yardstick, 2026-10-10).
# Usage: python tools/summarize_recruit_outcomes.py data/recruiting/recruit_outcomes.csv > data/recruiting/summary_tables.md
import csv,sys
from collections import defaultdict
rows=list(csv.DictReader(open(sys.argv[1])))
def get(Y,scheme,band,group,outcome):
    for r in rows:
        if r['class_year']==str(Y) and r['rank_scheme']==scheme and r['rank_band']==band and r['outcome_group']==group and r['outcome']==outcome:
            return int(r['count']),int(r['denominator'])
    return None
def pct(c,d): return f"{c}/{d} ({100*c/d:.0f}%)" if d else "-"
S='pipeline_overall_rank'; bands=['top25','26-100','101-200']
for Y in [2019,2020,2021,2022,2023,2024,'2019-2024']:
    print(f"\n### class {Y}")
    print("| band | n HS ranked | commit p4 | mid | low | non-D1 | not stated | HS drafted | HS signed | signed R1 | R2 | R3 | R4-5 | R6-10 | R11+ | drafted-unsigned | reached campus |")
    print("|---|"+"---|"*16)
    for b in bands:
        g=get(Y,S,b,'sample','ranked_hs_prospects')
        if not g: continue
        n=g[0]
        cells=[b,n]
        for t in ['p4','mid','low','non-D1','not stated']: cells.append(pct(get(Y,S,b,'a_commitment',t)[0],n))
        cells.append(pct(get(Y,S,b,'b_hs_draft','drafted')[0],n)); cells.append(pct(get(Y,S,b,'b_hs_draft','drafted_signed')[0],n))
        for rb in ['R1','R2','R3','R4-5','R6-10','R11+']: cells.append(get(Y,S,b,'b_hs_draft_signed_by_round',rb)[0])
        cells.append(get(Y,S,b,'b_hs_draft','drafted_unsigned')[0]); cells.append(pct(get(Y,S,b,'c_campus','reached_campus')[0],n))
        print("| "+" | ".join(map(str,cells))+" |")
print("\n### college draft of those who reached campus (classes with Y+4 available)")
print("| class | band | campus n | drafted Y+2 | drafted Y+3 | drafted Y+4 | drafted Y+3 or Y+4 | drafted any Y+2..4 | first pick R1 | R2 | R3 | R4-5 | R6-10 | R11+ | from p4 (Y+3) | mid | low | other | p4 commits later drafted | mid commits later drafted |")
print("|---|"+"---|"*19)
for Y in [2019,2020,2021,2022,'2019-2022']:
    for b in bands:
        g=get(Y,S,b,'c_campus','reached_campus')
        if not g: continue
        n=g[0]; cells=[Y,b,n]
        for k in (2,3,4):
            x=get(Y,S,b,f'd_college_draft_y+{k}','drafted'); cells.append(pct(x[0],x[1]) if x else '-')
        x=get(Y,S,b,'d_college_draft_y+3or4','drafted'); cells.append(pct(x[0],x[1]) if x else '-')
        x=get(Y,S,b,'d_college_draft_y+2to4','drafted'); cells.append(pct(x[0],x[1]) if x else '-')
        for rb in ['R1','R2','R3','R4-5','R6-10','R11+']:
            x=get(Y,S,b,'d_college_draft_y+2to4_first_by_round',rb); cells.append(x[0] if x else '-')
        for t in ['p4','mid','low','other']:
            x=get(Y,S,b,'d_college_draft_y+3_by_college_tier',t); cells.append(x[0] if x else '-')
        for t in ['p4','mid']:
            x=get(Y,S,b,'d_college_draft_y+2to4_by_commit_tier',t); cells.append(pct(x[0],x[1]) if x else '-')
        print("| "+" | ".join(map(str,cells))+" |")
print("\n### HS-ordinal bands, pooled 2019-2024")
H='hs_ordinal_rank'
print("| HS band | n | p4 | mid | HS signed | reached campus |")
print("|---|---|---|---|---|---|")
for b in ['hs1-10','hs11-25','hs26-50','hs51+']:
    n=get('2019-2024',H,b,'sample','ranked_hs_prospects')[0]
    print(f"| {b} | {n} | {pct(get('2019-2024',H,b,'a_commitment','p4')[0],n)} | {pct(get('2019-2024',H,b,'a_commitment','mid')[0],n)} | {pct(get('2019-2024',H,b,'b_hs_draft','drafted_signed')[0],n)} | {pct(get('2019-2024',H,b,'c_campus','reached_campus')[0],n)} |")
print("\n### HS-ordinal bands, 2019-2022 college draft")
print("| HS band | campus n | drafted Y+3 or Y+4 | drafted any Y+2..4 |")
print("|---|---|---|---|")
for b in ['hs1-10','hs11-25','hs26-50','hs51+']:
    x=get('2019-2022',H,b,'d_college_draft_y+3or4','drafted'); y=get('2019-2022',H,b,'d_college_draft_y+2to4','drafted')
    print(f"| {b} | {x[1]} | {pct(*x)} | {pct(*y)} |")
print("\n### background: HS seniors in each draft")
print("| draft | picks | HS SR picks | HS SR signed | R1 HS picks (signed) | R2 | R3 | R4-5 | R6-10 | R11+ |")
print("|---|---|---|---|---|---|---|---|---|---|")
for y in range(2019,2027):
    t=get(y,'all_hs_picks_in_draft','all','background','picks_total')[0]; h=get(y,'all_hs_picks_in_draft','all','background','hs_sr_picks')[0]; sg=get(y,'all_hs_picks_in_draft','all','background','hs_sr_signed')
    cells=[y,t,h,pct(*sg)]
    for rb in ['R1','R2','R3','R4-5','R6-10','R11+']:
        a=get(y,'all_hs_picks_in_draft',rb,'background','hs_sr_picks')[0]; b_=get(y,'all_hs_picks_in_draft',rb,'background','hs_sr_signed')[0]; cells.append(f"{a} ({b_})")
    print("| "+" | ".join(map(str,cells))+" |")
