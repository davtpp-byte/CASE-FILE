from pathlib import Path
import json,re,difflib,collections,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import episode
ROOT=Path(__file__).resolve().parents[1]
UP=ROOT.parent/'uploads'
draft=json.loads((UP/'draft_info.json').read_text())
materials={m['id']:m for m in draft['materials']['texts']}
segments=sorted([s for t in draft['tracks'] if t['type']=='text' for s in t['segments']],key=lambda s:s['target_timerange']['start'])
entries=[];units=[]
for i,segment in enumerate(segments):
 m=materials[segment['material_id']];tr=segment['target_timerange'];start=tr['start']/1e6;end=start+tr['duration']/1e6
 content=json.loads(m['content'])['text'];entries.append({'start':start,'end':end,'text':content,'index':i+1})
 for text,a,b in zip(m['words']['text'],m['words']['start_time'],m['words']['end_time']):
  if text.strip():units.append({'text':text,'start':start+a/1000,'end':min(end,start+b/1000),'caption':i+1})
srt=(UP/'captions_continuous.srt.md').read_text();captions=[]
for a,b,text in re.findall(r'(\d\d:\d\d:\d\d,\d{3})\s*-->\s*(\d\d:\d\d:\d\d,\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)',srt,re.S):captions.append({'start':episode.stamp(a),'end':episode.stamp(b),'text':text.strip()})
assert len(captions)==len(entries)
textdiff=[i+1 for i,(a,b) in enumerate(zip(captions,entries)) if a['text']!=b['text']]
maxclock=max(abs(a[k]-b[k]) for a,b in zip(captions,entries) for k in ['start','end'])
script=episode.parse_script((UP/'Untitled document (1).md').read_text());guide=episode.parse_guide((UP/'The_Last_Timeline_Real_Footage_Guide.md').read_text())
# Exact character ranges are retained; normalization only assists comparison.
numbers=dict(zip(('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety').split(),('0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 30 40 50 60 70 80 90').split()))
def tokenize(text):
 out=[]
 for m in re.finditer(r"[A-Za-z]+(?:[’'][A-Za-z]+)*|\d+(?:st|nd|rd|th)?",text):
  v=m[0].lower().replace('’',"'");v=re.sub(r'^(\d+)(?:st|nd|rd|th)$',r'\1',v);v=numbers.get(v,v)
  out.append({'value':v,'raw':m[0],'char_start':m.start(),'char_end':m.end()})
 return out
reference=tokenize(script['text']);transcript=[]
for ui,u in enumerate(units):
 for ti,t in enumerate(tokenize(u['text'])):
  transcript.append({**t,'unit':ui,'unit_token':ti,'start':u['start'],'end':u['end'],'caption':u['caption'],'timing_exact_start':ti==0})
a=[x['value'] for x in reference];b=[x['value'] for x in transcript];matcher=difflib.SequenceMatcher(None,a,b,autojunk=False)
index={};changes=[]
for tag,lo,hi,j,k in matcher.get_opcodes():
 if tag=='equal':index.update({lo+n:j+n for n in range(hi-lo)})
 else:changes.append({'operation':tag,'script':' '.join(x['raw'] for x in reference[lo:hi]),'caption':' '.join(x['raw'] for x in transcript[j:k]),'caption_number':transcript[j]['caption'] if j<len(transcript) else None,'start':transcript[j]['start'] if j<len(transcript) else None,'script_range':[lo,hi],'caption_range':[j,k]})
proposals=[]
for cue in guide['cues']:
 section=next(s for s in script['sections'] if s['key']==cue['chapter']);st=tokenize(section['text']);needle=[x['value'] for x in tokenize(cue['anchor'])];values=[x['value'] for x in st]
 matches=[i for i in range(len(st)-len(needle)+1) if values[i:i+len(needle)]==needle]
 assert len(matches)==1,(cue['id'],matches)
 charpos=section['char_start']+st[matches[0]]['char_start'];wi=next(i for i,x in enumerate(reference) if x['char_start']==charpos)
 j=index.get(wi);method='exact normalized text match'
 if j is None:
  # Candidate from aligned surrounding words. Never silently mark an ASR substitution confirmed.
  op=next((x for x in changes if x['script_range'][0]<=wi<x['script_range'][1]),None)
  if op and (op['script_range'][1]-op['script_range'][0])==(op['caption_range'][1]-op['caption_range'][0]) and op['caption_range'][0]<len(transcript):j=op['caption_range'][0]+wi-op['script_range'][0];method='substitution candidate; producer review required'
 if j is not None:
  t=transcript[j];p={'cue':cue['id'],'chapter':cue['chapter'],'anchor':cue['anchor'],'narration_start':t['start'] if t['timing_exact_start'] else None,'candidate_group_start':t['start'],'caption_number':t['caption'],'matched_caption_token':t['raw'],'source':cue['source_id'],'method':method,'precision':'provided timed-unit boundary' if t['timing_exact_start'] else 'inside a multiword unit: no individual word timestamp'}
 else:p={'cue':cue['id'],'chapter':cue['chapter'],'anchor':cue['anchor'],'method':'unresolved','source':cue['source_id']}
 proposals.append(p)
counts=collections.Counter((c['script'],c['caption']) for c in changes)
report={'draft_duration':draft['duration']/1e6,'draft_fps':draft['fps'],'caption_count':len(captions),'caption_text_differences_between_json_and_srt':textdiff,'maximum_timestamp_difference_json_vs_srt_seconds':maxclock,'timed_nonspace_units':len(units),'multi_token_units':sum(len(tokenize(u['text']))>1 for u in units),'script_normalized_tokens':len(reference),'caption_normalized_tokens':len(transcript),'exact_normalized_token_matches':len(index),'difference_spans':len(changes),'repeated_differences':[{'script':a,'caption':b,'count':n} for (a,b),n in counts.most_common()],'differences':changes,'cue_proposals':proposals,'audio_reference_filename':draft['materials']['audios'][0]['path'].replace('\\','/').split('/')[-1],'audio_uploaded':False,'srt_last_end':captions[-1]['end'],'private_metadata_excluded':True}
(ROOT/'qa/capcut-input-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
for k,v in report.items():
 if k not in ('differences','cue_proposals'):print(k,':',v)
print('\nCue alignment proposals:')
for p in proposals:print(p['cue'],p.get('narration_start'),p.get('caption_number'),p['method'],p.get('precision'))
