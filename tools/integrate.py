"""Build guarded lecture overlays and importable banks on GitHub, without changing existing banks."""
import time,pathlib,json,urllib.request,importlib.util,collections,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];SITE=ROOT/'.site-source';OUT=ROOT/'data/integration';OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('review',SITE/'scripts/review-lecture-links.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review);review.ROOT=SITE
TITLE={'tuijie-manual-upper':'腿姐背诵手册 · 上册','history-meetings':'党的重要会议-史纲','history-works':'毛著作总结-史纲','history-land':'土地政策-史纲','history-timeline':'史纲时间轴（打印版）','tuijie-manual-lower':'腿姐背诵手册 · 下册'}
REPOS={'tuijie-manual-upper':'zz-tuijie-manual-2027','history-meetings':'zz-history-notes-2027','history-works':'zz-history-notes-2027','history-land':'zz-history-notes-2027','history-timeline':'zz-history-notes-2027','tuijie-manual-lower':'zz-tuijie-manual-2027'}
def fetch(repo,name):
 with urllib.request.urlopen('https://raw.githubusercontent.com/aokid666/'+repo+'/main/data/'+name+'?verify='+str(time.time_ns()),timeout=90) as r:return json.load(r)
def dump(name,data):p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
UPPER_TEST_PAGES={19,20,31,32,38,43,53,54,58,86,87,98,99,104,119,120,131,132,143,144,157,158,181,182,194,195,208,209,221,222,234,235,244,245}
corpusdata={};sources=[];sourceDocs={}
for id,repo in REPOS.items():
 d=json.loads((ROOT/'data'/f'{id}.json').read_text()) if repo=='zz-history-notes-2027' else fetch(repo,id+'.json');base='https://aokid666.github.io/'+repo+'/'
 sourceDocs[id]=d
 for p in d['pages']:
  if (id.startswith('history-') or p['page']>=(11 if id=='tuijie-manual-upper' else 7)) and not (id=='tuijie-manual-upper' and p['page'] in UPPER_TEST_PAGES):corpusdata[id+':'+str(p['page'])]=p['text']
 sources.append({'id':id,'title':TITLE[id],'group':'history' if id.startswith('history-') else 'tuijie','pdfUrl':base+'pdf/'+id+'.pdf','dataUrl':base+'data/'+id+'.json','sha256':d['source']['sha256'],'pages':[{'page':p['page'],'width':p['width'],'height':p['height'],'url':base+f'img/{id}/{p["page"]:03}.{p["ext"]}','sha256':p['sha256'],'bytes':p['bytes'],'imageMethod':p['imageMethod']} for p in d['pages']]})
extra={group:review.Corpus('extra',{k:v for k,v in corpusdata.items() if k.startswith('history-')==(group=='history')},{}) for group in ['history','tuijie']}
new=[]
for repo,id in [('zz-tuijie-exams-2027','tuijie8'),('zz-tuijie-selftest-2027','tuijie-selftest')]:
 bank=fetch(repo,id+'.json');book=fetch(repo,'book.json');new.append((book,bank))
# Lower manual has only the exercises that can be located in the actual source.
try:
 bank=fetch('zz-tuijie-manual-2027','tuijie-manual-exercises.json');book=fetch('zz-tuijie-manual-2027','book.json')
 if bank['questions']:new.append((book,bank))
except urllib.error.HTTPError as e:
 if e.code!=404:raise
newqs=[q for book,bank in new for q in bank['questions']];newids={q['id'] for q in newqs};old=[q for q in review.pool() if q['id'] not in newids];allqs=old+newqs;groups=collections.defaultdict(dict);counts=collections.Counter();native=review.corpora();ksm=collections.defaultdict(dict)
for qi,q in enumerate(allqs):
 if qi%100==0:print('Matching source passages',qi,'/',len(allqs),flush=True)
 fs=review.facts(q);module=q.get('subject') or review.module_of(q)
 found=extra['tuijie'].find(fs,module='')+(extra['history'].find(fs,module='') if any(x in module for x in ['史纲','近现代史','毛泽东思想','毛中特']) else []);refs=list(q.get('extraLectures',[]))
 for hit in found:
  id,p=hit['page'].split(':');history=id.startswith('history-')
  if history and not any(x in module for x in ['史纲','近现代史','毛泽东思想','毛中特']):continue
  refs.append({'source':id,'page':int(p),'quote':hit['quote'],'method':hit['method']});counts['history' if history else 'tuijie']+=1
 group=q.get('bookId') or ('manual' if q.get('source')=='m' else 'original')
 if refs:groups[group][q['id']]={'sig':review.signature(q),'refs':refs}
 if q['id'] in newids:
  row={'sig':review.signature(q)}
  for kind,field in review.FIELDS.items():
   if q.get(field):continue
   hits=native[kind].find(fs,module)
   if hits:
    q[field]=[int(e['page']) if kind!='m' else e['page'] for e in hits];row[kind]=[{k:e[k] for k in ['page','quote']} for e in hits];q.setdefault('lectureEvidence',{})[kind]=row[kind];counts['new_'+kind]+=1
  ksm[group][q['id']]=row
for q in allqs:groups[q.get('bookId') or ('manual' if q.get('source')=='m' else 'original')]
for group,items in groups.items():dump(pathlib.Path('extra-links')/(group+'.json'),{'version':133,'items':items})
for group,items in ksm.items():dump(pathlib.Path('lecture-links')/(group+'.json'),{'version':133,'items':items})
for book,bank in new:
 dump(pathlib.Path('practice')/(book['id']+'.json'),bank)
 if book['id']=='tuijie8':raws=[fetch('zz-tuijie-exams-2027','tuijie8-question.json'),fetch('zz-tuijie-exams-2027','tuijie8-answer.json')]
 elif book['id']=='tuijie-manual-exercises':raws=[sourceDocs['tuijie-manual-upper']]
 else:raws=[fetch('zz-tuijie-selftest-2027','source-pages.json'),sourceDocs['tuijie-manual-lower']]
 pages=[{**{k:p[k] for k in ['width','height','bytes','sha256','ext','imageMethod']},'page':i+1,'sourcePage':p['page']} for i,p in enumerate([p for d in raws for p in d['pages']])]
 dump(pathlib.Path('manifests')/(book['id']+'.json'),{'id':book['id'],'pdfSha256':book['sha256'],'pages':pages,'pdfs':[d['source'] for d in raws]})
dump('books.json',[book for book,bank in new]);dump('extra-lectures.json',{'version':133,'title':'腿姐背诵手册','missingUpper':False,'sources':sources});dump('report.json',{'version':133,'questionsChecked':len(allqs),'newQuestions':len(newqs),'referenceCounts':dict(counts),'linkedQuestions':sum(map(len,groups.values())),'sourceSha256':{s['id']:s['sha256'] for s in sources}});print(json.dumps({'newQuestions':len(newqs),'counts':dict(counts)},ensure_ascii=False),flush=True)
