#!/usr/bin/env python3
"""Audit public EVERSENSE/Tilda pages, preserving precise original asset URLs."""
import json,re,os,hashlib,time
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urljoin,urlparse,urldefrag
from urllib.request import Request,urlopen
from html.parser import HTMLParser
BASE='https://ever-home.ru/'
OUT=Path('reference')
OUT.mkdir(exist_ok=True)
MAX_PAGES=100
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; EVERSENSE-Belarus-archive/1.0; +brand-owner)'}
class ResourceParser(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.assets=[];self.links=[];self.videos=[];self.meta=[];self.styles=[];self.groups=defaultdict(list)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('img','source','video','audio','link','script'):
   for k in ['src','srcset','poster','href','data-original','data-src','data-srcset','data-lazy-src','data-mobimg','data-mobile-image','data-cover-bg','data-bg','data-img-zoom-url']:
    if k not in a:continue
    v=a[k]
    if tag=='link' and k=='href' and a.get('rel') not in ['stylesheet'] and a.get('as') not in ['font','image','video']:continue
    for frag in (v.split(',') if k.endswith('srcset') else [v]):
     u=frag.strip().split(' ')[0]
     self.record(u,tag,k)
  for k,v in a.items():
   if k.startswith('data-') and ('https://' in str(v) or 'http://' in str(v)):
    for u in re.findall(r'https?://[^\s"\'<>]+',v): self.record(u,tag,k)
   if k=='style':
    for u in re.findall(r'url\([\s"\']*(.*?)["\']?\)',v):self.record(u,tag,'style-url')
  if tag=='a' and a.get('href'):self.links.append(a['href'])
  if tag=='meta' and a.get('content'):
   if a.get('property','').startswith('og:'):self.meta.append({'property':a.get('property'),'content':a['content']})
 def record(self,u,tag,k):
  u=u.strip(' "\'')
  if not u or u.startswith(('data:','#','mailto:','tel:','javascript:')):return
  if u.startswith('//'):u='https:'+u
  u=urljoin(BASE,u)
  if not urlparse(u).scheme.startswith('http'):return
  self.assets.append({'url':u,'tag':tag,'attribute':k})
 def handle_data(self,data):
  pass

def get(url,timeout=15,limit=6*1024*1024):
 try:
  with urlopen(Request(url,headers=HEADERS),timeout=timeout) as r:
   body=r.read(limit)
   return body,r.headers.get('Content-Type',''),r.status
 except Exception as e:return None,str(e),0

def canonical(url):
 u=urljoin(BASE,url)
 if not urlparse(u).netloc.endswith('ever-home.ru'):return None
 u=urldefrag(u)[0].split('?')[0].rstrip('/')
 if not u: u=BASE.rstrip('/')
 if re.search(r'\.(css|js|svg|png|jpg|jpeg|gif|webp|woff|woff2|pdf|zip|mp4|mov)$',u,re.I):return None
 return u

queue=[BASE,'https://ever-home.ru/catalog-ru','https://ever-home.ru/catalog-ru/new-minimalism-ru','https://ever-home.ru/catalog-ru/quiet-luxury-ru','https://ever-home.ru/catalog-ru/nature-aesthetic-ru','https://ever-home.ru/en','https://ever-home.ru/ru','https://ever-home.ru/where-to-buy-map-ru','https://ever-home.ru/where-to-buy-list-ru','https://ever-home.ru/where-to-buy-map-en','https://ever-home.ru/where-to-buy-list-en','https://ever-home.ru/politica-ru','https://ever-home.ru/politica-en']
robots,_,_=get(BASE+'robots.txt');sitemap_urls=[]
if robots:
 for u in re.findall(r'(?im)^sitemap:\s*(\S+)',robots.decode('utf8','ignore')):sitemap_urls.append(u)
sitemap_urls.append(BASE+'sitemap.xml')
for sm in set(sitemap_urls):
 txt,_,_=get(sm,limit=3*1024*1024)
 if txt:
  urls=re.findall(r'<loc>([^<]+)</loc>',txt.decode('utf8','ignore'))
  queue.extend(u for u in urls if '/catalog-ru' in u or u.rstrip('/')==BASE.rstrip('/'))
seen=set();pages=[];assets={}
while queue and len(pages)<MAX_PAGES:
 url=canonical(queue.pop(0))
 if not url or url in seen:continue
 seen.add(url)
 raw,ctype,status=get(url)
 if not raw or ('html' not in ctype.lower() and '<html' not in raw[:300].decode('utf8','ignore').lower()):continue
 html=raw.decode('utf8','replace');p=ResourceParser();p.feed(html)
 title=re.search(r'<title>(.*?)</title>',html,re.I|re.S)
 rec={'url':url,'title':re.sub(r'<.*?>','',title.group(1)) if title else '', 'html_bytes':len(raw),'status':status,'assets':[],'videos':[],'links':[],'tilda_blocks':[]}
 for a in p.assets:
  u=a['url'];asset=assets.setdefault(u,{'url':u,'uses':[]});asset['uses'].append({'page':url,'tag':a['tag'],'attr':a['attribute']});rec['assets'].append(u)
  if re.search(r'\.(mp4|mov|webm)(\?|$)',u,re.I):rec['videos'].append(u)
 for href in p.links:
  u=canonical(href)
  if u and u not in seen and u not in queue and len(queue)<200:
   if len(u.split('/'))<=6 and ('catalog' in u or 'product' in u or 'where-to-buy' in u or 'politica' in u or u.endswith('/en') or u.endswith('/ru') or u==BASE.rstrip('/')):queue.append(u)
  if u:rec['links'].append(u)
 # Tilda blocks
 rec['tilda_blocks']=re.findall(r'<div[^>]+class=["\'][^"\']*\bt-rec\b[^"\']*["\'][^>]+>',html)[:45]
 rec['assets']=list(dict.fromkeys(rec['assets']));rec['links']=list(dict.fromkeys(rec['links']))
 pages.append(rec)
 if url==BASE.rstrip('/'):(OUT/'original-home.html').write_text(html,encoding='utf8')
 if url.endswith('/catalog-ru'):(OUT/'original-catalog.html').write_text(html,encoding='utf8')
 print('PAGE',len(pages),status,rec['html_bytes'],len(rec['assets']),url,flush=True)

# Summarise image/video/font/script file URLs
for item in assets.values():
 item['use_count']=len(item['uses'])
 item['page_count']=len(set(u['page'] for u in item['uses']))
 item['uses']=item['uses'][:8]
for r in pages:r.pop('tilda_blocks',None)
unique=list(assets.values())
ext=Counter((urlparse(i['url']).path.rsplit('.',1)[-1].lower() if '.' in urlparse(i['url']).path else 'unknown') for i in unique)
summary={'pages_count':len(pages),'asset_urls_count':len(unique),'extensions':dict(ext),'hosts':dict(Counter(urlparse(i['url']).netloc for i in unique))}
(OUT/'audit.json').write_text(json.dumps({'summary':summary,'pages':pages,'assets':unique},ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'audit-summary.md').write_text('# Original EVERSENSE public site audit\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n\n## Pages\n'+'\n'.join('- '+x['url']+' ('+str(len(x['assets']))+' assets)' for x in pages)+'\n',encoding='utf8')
print('SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)