#!/usr/bin/env python3
"""Rebuild ./data.json from the newest WHOOP pull + manual.json.
Usage: python3 build.py [path/to/weekly/<date>.json]
   or: WHOOP_WEEKLY_DIR=/path/to/weekly python3 build.py   (default dir: ../whoop/weekly, outside this repo)
Times are written as local wall-clock time with no UTC offset. Published for viewing only."""
import json,os,sys,glob,statistics as st,datetime as dt
HERE=os.path.dirname(os.path.abspath(__file__))
# Merge every pull (oldest first, newer records win) so a short daily pull never shrinks history.
WHOOP_WEEKLY_DIR=os.environ.get('WHOOP_WEEKLY_DIR',os.path.join(HERE,'..','whoop','weekly'))
FILES=[sys.argv[1]] if len(sys.argv)>1 else sorted(glob.glob(os.path.join(WHOOP_WEEKLY_DIR,'*.json')))
SRC=FILES[-1]
d={'workouts':{},'recovery':{},'sleep':{},'cycles':{},'body':None}
for f in FILES:
    j=json.load(open(f))
    for k in ('workouts','recovery','sleep','cycles'):
        for r in j.get(k,[]): d[k][r['cycle_id'] if k=='recovery' else r['id']]=r
    if j.get('body'): d['body']=j['body']
for k in ('workouts','recovery','sleep','cycles'): d[k]=list(d[k].values())
M=json.load(open(os.path.join(HERE,'manual.json')))
LOCAL=dt.datetime.now().astimezone().tzinfo; NOW=dt.datetime.now(LOCAL)   # this machine's local zone; offsets are stripped on write
def T(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(LOCAL) if s else None
def r1(x,n=1): return None if x is None else round(x,n)
H=3600000
# ---- sleeps
sl=[]
for s in sorted(d['sleep'],key=lambda s:s['start']):
    sc=s.get('score') or {}; ss=sc.get('stage_summary') or {}; a,b=T(s['start']),T(s['end'])
    asleep=(ss.get('total_in_bed_time_milli',0)-ss.get('total_awake_time_milli',0)-ss.get('total_no_data_time_milli',0))/H if ss else None
    need=sc.get('sleep_needed')
    sl.append(dict(id=s['id'],cycle_id=s['cycle_id'],nap=s['nap'],start=a.isoformat(),end=b.isoformat(),wake_date=b.date().isoformat(),
      in_bed_h=r1(ss.get('total_in_bed_time_milli',0)/H,2),asleep_h=r1(asleep,2),
      light_h=r1(ss.get('total_light_sleep_time_milli',0)/H,2),deep_h=r1(ss.get('total_slow_wave_sleep_time_milli',0)/H,2),rem_h=r1(ss.get('total_rem_sleep_time_milli',0)/H,2),
      awake_h=r1(ss.get('total_awake_time_milli',0)/H,2),disturbances=ss.get('disturbance_count'),cycles=ss.get('sleep_cycle_count'),
      efficiency_pct=r1(sc.get('sleep_efficiency_percentage')),performance_pct=sc.get('sleep_performance_percentage'),
      consistency_pct=sc.get('sleep_consistency_percentage'),
      respiratory_rate=r1(sc.get('respiratory_rate'),2),need_h=r1(sum(need.values())/H,2) if need else None,score_state=s['score_state']))
# ---- workouts
wk=[]
for w in sorted(d['workouts'],key=lambda w:w['start']):
    sc=w.get('score') or {}; a,b=T(w['start']),T(w['end']); z=sc.get('zone_durations') or {}
    wk.append(dict(id=w['id'],date=a.date().isoformat(),start=a.isoformat(),sport=w['sport_name'],minutes=r1((b-a).total_seconds()/60),
      strain=r1(sc.get('strain'),1),avg_hr=sc.get('average_heart_rate'),max_hr=sc.get('max_heart_rate'),kj=r1(sc.get('kilojoule'),0),
      distance_m=sc.get('distance_meter'),zones_min={k.replace('_milli',''):r1(v/60000,1) for k,v in z.items()}))
# ---- days (one per WHOOP cycle)
days={}
for c in sorted(d['cycles'],key=lambda c:c['start']):
    sc=c.get('score') or {}
    days[c['id']]=dict(cycle_id=c['id'],cycle_start=T(c['start']).isoformat(),cycle_end=T(c['end']).isoformat() if c['end'] else None,
      day_strain=r1(sc.get('strain'),1),day_avg_hr=sc.get('average_heart_rate'),day_max_hr=sc.get('max_heart_rate'),day_kj=r1(sc.get('kilojoule'),0),steps=c.get('step_count'))
for r in d['recovery']:
    sc=r.get('score') or {}; dd=days.setdefault(r['cycle_id'],dict(cycle_id=r['cycle_id']))
    dd.update(recovery_pct=sc.get('recovery_score'),rhr=sc.get('resting_heart_rate'),hrv_ms=r1(sc.get('hrv_rmssd_milli')),
      spo2_pct=r1(sc.get('spo2_percentage')),skin_temp_c=r1(sc.get('skin_temp_celsius'),2),calibrating=sc.get('user_calibrating'),main_sleep_id=r['sleep_id'])
seen_main=0
for cid,dd in days.items():
    ms=[s for s in sl if s['cycle_id']==cid]
    main=[s for s in ms if s['id']==dd.get('main_sleep_id')] or [s for s in ms if not s['nap']]
    m=main[0] if main else None; naps=[s for s in ms if m is None or s['id']!=m['id']]
    dd['date']=(dt.datetime.fromisoformat(m['end']) if m else dt.datetime.fromisoformat(dd['cycle_start'])).date().isoformat()
    if m:
        seen_main+=1
        cons=m['consistency_pct']
        # WHOOP needs prior nights to score consistency; it reports 0 for the first main sleeps. Treat as not-yet-scored.
        if cons==0 and seen_main<=3: cons=None; m['consistency_pct']=None; m['consistency_note']='not scored: WHOOP calibrating (API reported 0)'
        dd.update(bedtime=m['start'][11:16],wake=m['end'][11:16],main_sleep_h=m['asleep_h'],main_in_bed_h=m['in_bed_h'],deep_h=m['deep_h'],rem_h=m['rem_h'],
          sleep_eff_pct=m['efficiency_pct'],sleep_perf_pct=m['performance_pct'],sleep_consistency_pct=cons,resp_rate=m['respiratory_rate'],
          disturbances=m['disturbances'],sleep_need_h=m['need_h'])
    dd['nap_count']=len(naps); dd['nap_h']=r1(sum(s['asleep_h'] or 0 for s in naps),2)
    dd['total_sleep_h']=r1((m['asleep_h'] if m else 0)+dd['nap_h'],2)
    ce=dd.get('cycle_end')
    ws=[w for w in wk if dd['cycle_start']<=w['start'] and (ce is None or w['start']<ce)]
    dd['workouts']=[w['id'] for w in ws]; dd['workout_min']=r1(sum(w['minutes'] for w in ws))
    dd['cycle_hours']=r1((dt.datetime.fromisoformat(ce or NOW.isoformat())-dt.datetime.fromisoformat(dd['cycle_start'])).total_seconds()/3600)
    dd['ongoing']=ce is None
    dd['note']=None
out=sorted(days.values(),key=lambda x:x['cycle_start'])
for x in out:
    if x.get('recovery_pct') is None: x['note']='First WHOOP cycle, no recovery scored' if x is out[0] else None
    for a in M.get('annotations',[]):
        if x['cycle_start'].startswith(a['cycle_start_prefix']): x['note']=a['note']
    if x['cycle_hours'] and x['cycle_hours']>30 and not x['note']:
        x['note']=f"Long WHOOP cycle ({x['cycle_hours']:.0f} h): no new main sleep, only naps, until the next one"
# ---- body, zones, derived
body=d.get('body') or {}
prev=os.path.join(HERE,'data.json')
oldp=json.load(open(prev)).get('profile',{}) if os.path.exists(prev) else {}
h=body.get('height_meter') or oldp.get('height_m'); kg=body.get('weight_kilogram') or oldp.get('weight_kg'); mx=body.get('max_heart_rate') or oldp.get('max_hr_whoop') or 180
prof=dict(M['profile']); prof.update(height_m=r1(h,2),weight_kg=r1(kg,1),bmi=r1(kg/h/h,1) if h and kg else None,max_hr_whoop=mx)
rh=[x['rhr'] for x in out if x.get('rhr') is not None][-30:]; rb=st.median(rh) if rh else 60
Z=lambda p:round(rb+p*(mx-rb))
zones={"method":"heart rate reserve (Karvonen), WHOOP's default: bpm = RHR + pct x (maxHR - RHR). Estimated with WHOOP max HR and 30-cycle median RHR; WHOOP's own cutoffs (in app settings) may differ slightly and recalibrate monthly.",
 "max_hr":mx,"rhr_baseline":rb,"zone0_below_40pct":[0,Z(.4)],"zone1_40_60pct":[Z(.4),Z(.6)],"zone2_60_70pct":[Z(.6),Z(.7)],"zone3_70_80pct":[Z(.7),Z(.8)],"zone4_80_90pct":[Z(.8),Z(.9)],"zone5_90_100pct":[Z(.9),mx]}
def buckets():
    B=[]
    for lo,hi,lab in [(0,3,'under 3 h'),(3,4.5,'3-4.5 h'),(4.5,6,'4.5-6 h'),(6,99,'6 h+')]:
        g=[x for x in out if x.get('recovery_pct') is not None and x.get('main_sleep_h') is not None and lo<=x['main_sleep_h']<hi]
        B.append(dict(label=lab,min_h=lo,max_h=None if hi==99 else hi,n=len(g),avg_recovery=r1(st.mean(x['recovery_pct'] for x in g),0) if g else None,show=len(g)>=5))
    p=[(x['main_sleep_h'],x['recovery_pct']) for x in out if x.get('recovery_pct') is not None and x.get('main_sleep_h') is not None]
    r=round(st.correlation(*zip(*p)),2) if len(p)>=5 else None
    return dict(r_main_sleep_vs_recovery=r,n=len(p),buckets=B,min_n_to_show=5)
def ref_bands():
    """Copy manual.json reference_bands and add your current value + category. Population bands are references, not your data."""
    import copy
    RB=copy.deepcopy(M.get('reference_bands',{})); ML=M['manual_logs']
    sc=[x for x in out if x.get('recovery_pct') is not None]  # scored cycles
    def ser(f): return [x[f] for x in sc if x.get(f) is not None]
    def agg(v,a): return None if not v else (st.median(v) if a=='median' else st.mean(v))
    def cat(bands,v):
        if v is None or not isinstance(bands,list): return None
        for b in bands:
            if (b.get('min') is None or v>=b['min']) and (b.get('max') is None or v<b['max']): return b['label']
    def split_s(t):
        try: m,s_=str(t).split(':'); return int(m)*60+float(s_)
        except Exception: return None
    for k,r in RB.items():
        if k.startswith('_'): continue
        cf=r.pop('current_from',{}); cur=dict(value=None,window=None,recent=None,n=0,category=None,recent_category=None)
        if 'field' in cf and cf['field']=='sleep_per_24h':
            w=sc[-cf['window']:]
            if w:
                a=dt.datetime.fromisoformat(w[0]['cycle_start']); b=dt.datetime.fromisoformat(w[-1]['cycle_end'] or NOW.isoformat())
                cur.update(value=r1(sum(x.get('total_sleep_h') or 0 for x in w)/((b-a).total_seconds()/86400),2),window=f"{len(w)} cycles, total asleep / elapsed days",n=len(w))
                rw=sc[-cf.get('recent_window',7):]; a7=dt.datetime.fromisoformat(rw[0]['cycle_start']); b7=dt.datetime.fromisoformat(rw[-1]['cycle_end'] or NOW.isoformat())
                cur.update(recent=r1(sum(x.get('total_sleep_h') or 0 for x in rw)/((b7-a7).total_seconds()/86400),2),recent_window=f"last {len(rw)} cycles, total asleep / elapsed days")
                ms=ser('main_sleep_h')[-30:]; cur['main_block_median_h']=r1(st.median(ms),2) if ms else None; cur['main_block_7avg_h']=r1(st.mean(ms[-7:]),2) if ms else None
        elif 'field' in cf and cf['field']=='weekly_cardio_modeq':
            W={}
            for w_ in wk:
                d0=dt.date.fromisoformat(w_['date']); mon=d0-dt.timedelta(days=d0.weekday()); z=w_['zones_min'] or {}
                W[mon]=W.get(mon,0)+z.get('zone_one',0)+2*sum(z.get(q,0) for q in ('zone_two','zone_three','zone_four','zone_five'))
            thisw=NOW.date()-dt.timedelta(days=NOW.date().weekday()); first=min(W) if W else thisw
            full=[]; m_=thisw-dt.timedelta(days=7)
            while m_>=first and len(full)<cf['window']: full.append((m_.isoformat(),round(W.get(m_,0)))); m_-=dt.timedelta(days=7)
            full.reverse()
            cur.update(value=round(st.mean(v for _,v in full)) if full else None,window=f"mean of last {len(full)} full Mon-Sun weeks",n=len(full),weeks=full,
                       this_week_so_far=round(W.get(thisw,0)),weeks_meeting_150=sum(v>=150 for _,v in full))
        elif 'field' in cf:
            v=ser(cf['field']); w=v[-cf['window']:]
            cur.update(value=r1(agg(w,cf['agg']),1),window=f"{cf['agg']} of last {len(w)} scored cycles",n=len(w))
            if cf.get('recent_window'): cur['recent']=r1(agg(v[-cf['recent_window']:],cf['recent_agg']),1); cur['recent_window']=f"{cf['recent_agg']} of last {min(len(v),cf['recent_window'])} scored cycles"
            if v: cur['range']=[min(w),max(w)]
        elif cf.get('special')=='row_steady':
            mn=cf.get('min_minutes',30); thisw=NOW.date()-dt.timedelta(days=NOW.date().weekday())
            rows=[w_ for w_ in wk if w_['sport']=='rowing' and (w_['minutes'] or 0)>=mn]
            def wkof(w_): d0=dt.date.fromisoformat(w_['date']); return d0-dt.timedelta(days=d0.weekday())
            first=min([wkof(x) for x in wk],default=thisw); full=[]; m_=thisw-dt.timedelta(days=7)
            while m_>=first and len(full)<cf['window']: full.append((m_.isoformat(),sum(wkof(x)==m_ for x in rows))); m_-=dt.timedelta(days=7)
            full.reverse()
            cur.update(value=round(sum(v for _,v in full)/len(full),2) if full else None,window=f"mean of last {len(full)} full Mon-Sun weeks",n=len(full),weeks=full,
                       this_week_so_far=sum(wkof(x)==thisw for x in rows),total_banked=len(rows),last_row=rows[-1]['date'] if rows else None)
        elif 'profile' in cf:
            cur.update(value=prof.get(cf['profile']),window='latest WHOOP body measurement',n=1)
        elif 'manual_log' in cf:
            L=ML.get(cf['manual_log'],[])
            if cf.get('test'): L=[x for x in L if x.get('test')==cf['test']]
            if cf['manual_log']=='blood_pressure':
                L=L[-cf['window']*2:]
                if L:
                    sy=[e[q] for e in L for q in ('sys1','sys2') if e.get(q)]; di=[e[q] for e in L for q in ('dia1','dia2') if e.get(q)]
                    if sy and di: cur.update(value=round(st.mean(sy)),value_diastolic=round(st.mean(di)),display=f"{round(st.mean(sy))}/{round(st.mean(di))}",window=f"mean of {len(L)} session{'' if len(L)==1 else 's'}",n=len(L))
            elif L:
                vk=cf.get('value_key')
                if cf['manual_log']=='erg' and cf.get('test')=='2k': vals=[x.get('time_s') for x in L if x.get('time_s')]; val=min(vals) if vals else None
                else:
                    vals=[split_s(x.get(vk)) if vk=='avg_split_500m' else x.get(vk) for x in L]; vals=[x for x in vals if x is not None]
                    val=(st.mean(vals[-cf.get('window',len(vals)):]) if cf.get('agg')=='mean' else vals[-1]) if vals else None
                if val is not None and cf.get('divide_by_height_cm') and prof.get('height_m'): val=round(val/(prof['height_m']*100),3)
                cur.update(value=r1(val,3) if val is not None else None,window={'best':'best logged','latest':'latest logged','mean':f"mean of last {min(len(vals),cf.get('window',len(vals)))} logged"}.get(cf.get('agg'),cf.get('agg')),n=len(vals))
            if cur['value'] is None: cur['window']='not logged yet'
        if r.get('bands')=='personal_baseline_sd':
            v=ser('skin_temp_c')[-30:]
            if len(v)>=5:
                md,sd=st.median(v),st.pstdev(v); f=lambda q:round(md+q*sd,2)
                r['bands']=[dict(min=None,max=f(-2),label="Well below baseline (< -2 SD)",tone="watch"),dict(min=f(-2),max=f(-1),label="Below baseline (-1 to -2 SD)",tone="ok"),
                            dict(min=f(-1),max=f(1),label="At baseline (within 1 SD)",tone="good"),dict(min=f(1),max=f(2),label="Above baseline (+1 to +2 SD)",tone="ok"),dict(min=f(2),max=None,label="Well above baseline (> +2 SD): illness watch",tone="flag")]
                r['baseline']=dict(median_c=r1(md,2),sd_c=r1(sd,2),n=len(v))
        if k=='blood_pressure':
            # worse of systolic and diastolic band (bands = systolic, bands_diastolic = diastolic; same min/max/label layout)
            rank=[b['label'] for b in r['bands']]
            cs=cat(r['bands'],cur['value']); cd=cat(r.get('bands_diastolic',[]),cur.get('value_diastolic'))
            cur['category_systolic']=cs; cur['category_diastolic']=cd
            cur['category']=max([c_ for c_ in (cs,cd) if c_],key=rank.index) if (cs or cd) else None
        else:
            cur['category']=cat(r['bands'],cur['value']); cur['recent_category']=cat(r['bands'],cur.get('recent'))
        r['current']=cur
        g=M.get('goals',{}).get(r.get('goal_id')) if r.get('goal_id') else None
        r['goal']=dict(id=r['goal_id'],target=g.get('target'),timeframe=g.get('timeframe'),status=g['status']) if g else None
        r['goal_status']=g['status'] if g else None
    return RB
def vo2max_est():
    """Estimated VO2max from your own data. Estimates, not measurements; lab result goes in manual_logs.vo2max_lab."""
    sc=[x for x in out if x.get('rhr') is not None]; age=prof['age']; bmi=prof['weight_kg']/prof['height_m']**2; HM=prof['max_hr_whoop']
    obs_max=max((w['max_hr'] for w in wk if w.get('max_hr')),default=None); tanaka=round(208-0.7*age,1)
    uth=lambda hr,mx=HM: round(15.3*mx/hr,1)
    thisw=(NOW.date()-dt.timedelta(days=NOW.date().weekday())).isoformat()
    r7=st.mean(x['rhr'] for x in sc[-7:]); best=min(x['rhr'] for x in sc); med=st.median(x['rhr'] for x in sc[-30:])
    # activity rating from WHOOP-tracked aerobic sports over the last 4 full weeks (Jackson PA-R 0-7)
    AER={'swimming','rowing','running','cycling','spin','walking'}; mon=dt.date.fromisoformat(thisw); start=mon-dt.timedelta(days=28)
    aer=sum(w['minutes'] for w in wk if w['sport'] in AER and start<=dt.date.fromisoformat(w['date'])<mon)/4
    mod=sum(w['minutes'] for w in wk if w['sport'] not in AER and start<=dt.date.fromisoformat(w['date'])<mon)/4
    if aer>0: par=4 if aer<30 else 5 if aer<=60 else 6 if aer<=180 else 7
    else: par=3 if mod>60 else 2 if mod>=10 else 1
    srpa={0:0,1:0,2:0,3:0.32,4:0.32,5:1.06,6:1.76,7:3.03}[par]
    jack=round(56.363+1.921*par-0.381*age-0.754*bmi+10.987,1)
    jurca=round((18.07+2.77-0.10*age-0.17*bmi-0.03*r7+srpa)*3.5,1)
    U=uth(r7)
    jurca_f=lambda hr: round((18.07+2.77-0.10*age-0.17*bmi-0.03*hr+srpa)*3.5,1)
    blend=lambda hr: round(st.mean([uth(hr),jack,jurca_f(hr)]),1)
    # trend: same 3-method blend as the headline; only RHR varies (activity rating + BMI held at current values)
    ser=[]
    for i,x in enumerate(sc):
        w=[y['rhr'] for y in sc[max(0,i-6):i+1]]
        if len(w)>=3: rm=st.mean(w); ser.append(dict(cycle_start=x['cycle_start'],date=x['date'],rhr_7avg=round(rm,1),n=len(w),est=blend(rm),est_hr_only=uth(rm),est_jackson=jack,est_jurca=jurca_f(rm)))
    W={}
    for x in sc:
        d0=dt.date.fromisoformat(x['date']); W.setdefault((d0-dt.timedelta(days=d0.weekday())).isoformat(),[]).append(x['rhr'])
    weekly=[dict(week=k,rhr_mean=round(st.mean(v),1),n=len(v),est=blend(st.mean(v)),est_hr_only=uth(st.mean(v)),partial=(k==thisw or len(v)<4)) for k,v in sorted(W.items())]
    methods=[
     dict(id="uth_sorensen",name="Uth-Sorensen heart rate ratio",value=U,inputs=dict(hrmax=HM,hrmax_source="WHOOP max HR (not lab-measured; equals age-predicted)",hrrest=round(r7,1),hrrest_source="7-cycle mean WHOOP sleeping RHR"),
          formula="15.3 x HRmax / HRrest",see="2.7 ml/kg/min with measured HRmax, 4.7 with age-predicted HRmax (well-trained men 21-51)",in_headline=True,
          source=dict(label="Uth et al. 2004, Eur J Appl Physiol",url="https://doi.org/10.1007/s00421-003-0988-y")),
     dict(id="jackson_1990_bmi",name="Jackson 1990 non-exercise (NASA PA-R, BMI)",value=jack,inputs=dict(age=age,sex="male",bmi=round(bmi,2),par=par,par_basis=f"{aer:.0f} min/wk of swim/row (WHOOP) avg of last 4 full weeks"),
          formula="56.363 + 1.921 PA-R - 0.381 age - 0.754 BMI + 10.987 (male)",see="5.6-5.7 ml/kg/min",in_headline=True,
          source=dict(label="Jackson et al. 1990, Med Sci Sports Exerc 22:863",url="https://doi.org/10.1249/00005768-199012000-00021")),
     dict(id="jurca_2005_nasa",name="Jurca 2005 non-exercise (NASA model, with RHR)",value=jurca,inputs=dict(age=age,sex="male",bmi=round(bmi,2),rhr=round(r7,1),sr_pa_coef=srpa,sr_pa_basis=f"PA-R {par} mapped to Jurca 5-level scale"),
          formula="METs = 18.07 + 2.77 (male) - 0.10 age - 0.17 BMI - 0.03 RHR + SR-PA; x 3.5",see="1.45 METs = 5.1 ml/kg/min",in_headline=True,
          source=dict(label="Jurca et al. 2005, Am J Prev Med 29:185",url="https://doi.org/10.1016/j.amepre.2005.06.004")),
    ]
    sens=[dict(id="uth_best_rhr",value=uth(best),note=f"Uth with best RHR {best:.0f}"),dict(id="uth_median_rhr",value=uth(med),note=f"Uth with 30-cycle median RHR {med:.0f}"),
          dict(id="uth_tanaka",value=uth(r7,tanaka),note=f"Uth with Tanaka HRmax {tanaka}"),dict(id="uth_observed_max",value=uth(r7,obs_max) if obs_max else None,note=f"Uth with highest HR seen in a workout ({obs_max}); true max is at least this")]
    hv=[m['value'] for m in methods if m['in_headline']]; h=round(st.mean(hv),1)
    lo=round(min(min(hv),h-5),0); hi=round(max(max(hv),h+5),0)
    return dict(_about="ESTIMATES from WHOOP data + profile, not a measurement. Compare with manual_logs.vo2max_lab once tested.",unit="ml/kg/min",
      headline=dict(value=h,low=lo,high=hi,basis="mean of the 3 methods; range = wider of the method spread or +/-5 (typical SEE)"),
      methods=methods,sensitivity=sens,not_used=[dict(id="hunt_nes_2011",reason="needs waist circumference (not measured yet) and a HUNT activity index")],
      series_method="Blended estimate (same 3-method mean as the headline) on the rolling 7-cycle mean RHR (>=3 cycles); activity rating and BMI held at current values, so only RHR moves the line. The latest point equals the headline.",
      series_label="estimated VO2max, 3-method blend",series=ser,weekly=weekly,
      hr_only=dict(label="heart-rate method only (Uth-Sorensen)",note="Reads higher than the blended headline; kept for comparison.",_fields="series[].est_hr_only, weekly[].est_hr_only"),
      lab=M['manual_logs'].get('vo2max_lab',[]))
today=NOW.date().isoformat()
status=[s for s in M['manual_logs'].get('status',[]) if s.get('active') and s['date']<=today and (s.get('until') is None or s['until']>=today)]
VE=vo2max_est(); RBX=ref_bands()
if 'vo2max' in RBX: RBX['vo2max']['source']={'label':"The Cooper Institute, VO2max norms for men 40-49: Poor under 38.5, Fair 38.5-42.3, Good 42.4-46.3, Excellent 46.4-52.4, Superior 52.5+ (credit: The Cooper Institute)"}
if 'vo2max' in RBX:
    c=RBX['vo2max']['current']; lab=c['value']
    cat_=lambda v: next((b['label'] for b in RBX['vo2max']['bands'] if (b['min'] is None or v>=b['min']) and (b['max'] is None or v<b['max'])),None)
    c.update(lab=lab,estimated=VE['headline']['value'],estimated_range=[VE['headline']['low'],VE['headline']['high']],estimated_category=cat_(VE['headline']['value']),
             estimated_range_categories=[cat_(VE['headline']['low']),cat_(VE['headline']['high'])])
    if lab is None: c.update(value=VE['headline']['value'],category=cat_(VE['headline']['value']),basis="estimated",window="estimated (mean of 3 methods), not a lab test")
    else: c['basis']="lab"
data={"meta":{"generated":NOW.isoformat(timespec='minutes'),"timezone":"Local wall-clock time, no UTC offset; converted from WHOOP UTC",
  "source":f"WHOOP API v2, {len(FILES)} pulls merged, newest {os.path.basename(SRC)}","history_from":out[0]['cycle_start'][:10],"history_to":today,"notes":[
  "One 'day' = one WHOOP physiological cycle, which starts when a main sleep starts. You often sleep late afternoon/evening, so two cycles can share a calendar date, and a cycle can run >30 h when only naps follow. Use cycle_start as the x-axis key.",
  "total_sleep_h = main sleep + naps in that cycle (asleep time). sleep_consistency_pct is null while WHOOP was still calibrating (first 3 main sleeps reported 0).",
  "For an ongoing cycle, recovery/RHR/HRV/SpO2/resp/sleep are final (scored at wake); only strain/steps/workouts are still accumulating.",
  "Generated by build.py from the WHOOP pull + manual.json. Edit manual.json, not this file. Published for viewing only."]},
 "profile":prof,"hr_zones":zones,
 "vo2max_est":VE,"reference_bands":RBX,"goals":M.get('goals',{}),
 "insights":{"sleep_vs_recovery":buckets()},
 "status_active":status,"coach_copy":M['coach_copy'],
 "days":out,"sleeps":sl,"workouts":wk,"manual_logs":M['manual_logs']}
p=os.path.join(HERE,'data.json'); tmp=p+'.tmp'
fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
import re as _re
_OFF=_re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)(?:[+-]\d{2}:\d{2}|Z)$')
def _naive(o):   # local wall-clock time, no UTC offset, in every ISO string
    if isinstance(o,dict): return {k:_naive(v) for k,v in o.items()}
    if isinstance(o,list): return [_naive(v) for v in o]
    if isinstance(o,str):
        m=_OFF.match(o); return m.group(1) if m else o
    return o
data=_naive(data)
with os.fdopen(fd,'w') as f: json.dump(data,f,indent=1,ensure_ascii=False)
os.replace(tmp,p); print(f"data.json rebuilt from {os.path.basename(SRC)}: {len(out)} cycles, {len(wk)} workouts, status flags active: {len(status)}")
