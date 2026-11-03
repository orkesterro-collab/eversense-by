#!/usr/bin/env python3
"""Build the licensed EVERSENSE static Tilda mirror from public originals.
Copies available Tilda assets and preserves layout, scripts, image references.
Leaves unavailable media as original URL and reports it honestly.
"""
import io,json,os,re,hashlib,sys,time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.parse import urlparse,urljoin,urldefrag,unquote
from urllib.request import Request,urlopen
from urllib.error import HTTPError

BASE='https://ever-home.ru'
PUBLIC_BASE='/eversense-by/'
ROOT=Path('.')
MEDIA=ROOT/'assets'/'original-tilda'
MEDIA.mkdir(parents=True,exist_ok=True)
AUDIT=json.loads((ROOT/'reference/audit.json').read_text(encoding='utf-8'))
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; EVERSENSE-Belarus-project/1.0; distributor)', 'Accept':'*/*'}
MAX_BYTES=15*1024*1024
VIDEO_MAX=40*1024*1024

try:
 from PIL import Image
except ImportError:
 Image=None

def request(url,maxbytes=MAX_BYTES):
 try:
  with urlopen(Request(url,headers=HEADERS),timeout=22) as r:
   length=int(r.headers.get('content-length') or 0)
   if length>maxbytes:return None,f'too large: {length} bytes'
   data=r.read(maxbytes+1)
   if len(data)>maxbytes:return None,'stream exceeded size limit'
   return data,None
 except Exception as e:return None,str(e)[:180]

def ext_for(u):
 e=urlparse(u).path.lower().rsplit('.',1)[-1]
 return e if e in {'jpeg','jpg','png','svg','webp','css','js','gif','woff','woff2','mp4','webm','ico','pdf','ttf','otf'} else 'bin'

def local_name(url):
 ext=ext_for(url)
 if ext in ('jpeg','jpg','png','gif') and Image:ext='webp'
 base=unquote(urlparse(url).path.rsplit('/',1)[-1]).rsplit('.',1)[0]
 base=re.sub(r'[^A-Za-z0-9_-]+','-',base)[:38] or 'media'
 return f'{hashlib.sha256(url.encode()).hexdigest()[:12]}-{base}.{ext}'

def download_asset(info):
 url=info['url'];ext=ext_for(url)
 if not url.startswith(('https://static.tildacdn.com/','https://neo.tildacdn.com/','https://dl.dropboxusercontent.com/','https://ever-home.ru/custom.css','https://cdnjs.cloudflare.com/')):
  return {'url':url,'status':'external','local':None}
 name=local_name(url);target=MEDIA/name
 if target.exists():return {'url':url,'status':'cached','local':str(target),'bytes':target.stat().st_size}
 limit=VIDEO_MAX if ext in ('mp4','webm') else MAX_BYTES
 data,error=request(url,limit)
 if error:return {'url':url,'status':'missing','error':error,'type':ext,'local':None}
 try:
  if ext in ('jpeg','jpg','png','gif') and Image:
   im=Image.open(io.BytesIO(data));im.load()
   if max(im.size)>2500:
    im.thumbnail((2500,2500),Image.Resampling.LANCZOS)
   # Preserve alpha for transparent overlays.
   if im.mode not in ('RGB','RGBA'):im=im.convert('RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB')
   im.save(target,'WEBP',quality=88,method=5)
  else:target.write_bytes(data)
  return {'url':url,'status':'saved','local':str(target),'bytes':target.stat().st_size,'input_bytes':len(data),'type':ext}
 except Exception as e:
  return {'url':url,'status':'missing','error':'conversion: '+str(e)[:150],'type':ext,'local':None}

assets=AUDIT['assets'];results=[]
print('Downloading',len(assets),'assets...',flush=True)
with ThreadPoolExecutor(max_workers=14) as pool:
 futures=[pool.submit(download_asset,a) for a in assets]
 for n,f in enumerate(as_completed(futures),1):
  row=f.result();results.append(row)
  if n%40==0:print('ASSETS',n,'saved',sum(x['status'] in ('saved','cached') for x in results),'failed',sum(x['status']=='missing' for x in results),flush=True)
lookup={r['url']:r for r in results}

# Build all captured pages, preserving the exact HTML structure / original Tilda CSS/JS behaviour.
# All copied media references are local. Third-party Tilda CSS/JS runtime is kept live,
# with saved copies present for later self-hosted migration.
def output_path(url):
 u=urlparse(url);path=u.path.strip('/')
 if not path:return ROOT/'index.html'
 return ROOT/path/'index.html'

def rewrite_page(page):
 url=page['url'];dest=output_path(url)
 dest.parent.mkdir(parents=True,exist_ok=True)
 # Source pages were available via public paths, keep full HTML before patching.
 data,err=request(url,5*1024*1024)
 if err:return {'url':url,'status':'missing','error':err}
 h=data.decode('utf-8','replace')
 # Replace asset URLs with relative local paths in HTML only for downloaded media.
 # Leave CSS/JS on Tilda CDN while separately preserving binaries in repository.
 replacements=0
 for remote in sorted(set(page.get('assets',[])),key=len,reverse=True):
  info=lookup.get(remote)
  if not info or info.get('status') not in ('saved','cached'):continue
  ext=ext_for(remote)
  if ext not in ('jpg','jpeg','png','gif','webp','svg','mp4','webm') and not (remote.startswith('https://ever-home.ru/custom.css') or remote.startswith('https://cdnjs.cloudflare.com/')):continue
  target=Path(info['local'])
  rel=os.path.relpath(target,dest.parent).replace('\\','/')
  if remote in h:
   h=h.replace(remote,rel);replacements+=1
 # Some Tilda stylesheets are referenced by root-relative /custom.css links.
 # Map each versioned stylesheet to its exact saved file, otherwise GitHub Pages returns 404.
 for remote, info in lookup.items():
  if not remote.startswith('https://ever-home.ru/custom.css') or info.get('status') not in ('saved','cached'):continue
  src='/custom.css'+(('?'+remote.split('?',1)[1]) if '?' in remote else '')
  if src in h:
   rel=os.path.relpath(Path(info['local']),dest.parent).replace('\\\\','/')
   h=h.replace(src,rel)
 # Preserve internal links but redirect them to copied GitHub Pages routes.
 h=re.sub(r'''(?i)(href|action)=(['"])(https?://(?:www\.)?ever-home\.ru)(/[^'"<>]*)\2''',lambda m:m.group(1)+'='+m.group(2)+PUBLIC_BASE+m.group(4).lstrip('/')+m.group(2),h)
 h=re.sub(r'''(?i)(href|action)=(['"])(https?://(?:www\.)?ever-home\.ru)\2''',lambda m:m.group(1)+'='+m.group(2)+PUBLIC_BASE+m.group(2),h)
 # Root-relative navigation would otherwise escape the project path.
 h=re.sub(r'''(?i)(href|action)=(['"])/(?!/|eversense-by/)([^'"<>]*)\2''',lambda m:m.group(1)+'='+m.group(2)+PUBLIC_BASE+m.group(3)+m.group(2),h)
 # Russian Belarus-specific replacements in contact CTA links. Keep factory info as original source reference.
 h=h.replace('https://ever-home.ru/where-to-buy-list-ru',PUBLIC_BASE+'where-to-buy.html')
 h=h.replace(PUBLIC_BASE+'where-to-buy-list-ru',PUBLIC_BASE+'where-to-buy.html')
 h=h.replace(PUBLIC_BASE+'where-to-buy-map-ru',PUBLIC_BASE+'where-to-buy.html')
 h=h.replace('https://ever-home.ru/where-to-buy-ru',PUBLIC_BASE+'where-to-buy.html')
 h=h.replace('<title>EVERSENSE |','<title>EVERSENSE Беларусь |')
 h=re.sub(r'<meta\s+name="robots"[^>]*>', '<meta name="robots" content="noindex,nofollow">',h,count=1)
 # Prevent analytics from original website collecting visits to the preview.
 h=h.replace('https://mc.yandex.ru/metrika/tag.js','about:blank')
 # Attach distributor disclaimer in footer (no fake addresses, phone or prices).
 # Insert the consistent distributor legal block after the original Tilda footer.
 css_rel=os.path.relpath(ROOT/'assets'/'belarus-footer.css',dest.parent).replace(chr(92),'/')
 h=h.replace('</head>','<link rel="stylesheet" href="'+css_rel+'"></head>',1)
 if dest==ROOT/'index.html':
  h=h.replace('</head>','<link rel="stylesheet" href="assets/home-footer-trim.css"></head>',1)
 h=h.replace('</body>',"<section class=\"ev-belarus-legal\" aria-label=\"Реквизиты представителя EVERSENSE в Беларуси\"><div class=\"ev-belarus-legal__inner\"><div><p class=\"ev-belarus-legal__eyebrow\">EVERSENSE · Беларусь</p><h2 class=\"ev-belarus-legal__heading\">Представитель торговой марки EVERSENSE<br>на территории Республики Беларусь</h2></div><div><p class=\"ev-belarus-legal__detail\"><strong>ООО «Флорсток»</strong></p><p class=\"ev-belarus-legal__detail\">УНП 192608003</p><p class=\"ev-belarus-legal__detail\">220062, Республика Беларусь, г. Минск,<br>пр. Победителей, д. 129, пом. 358</p><p class=\"ev-belarus-legal__detail\">Тел.: <a class=\"ev-belarus-legal__phone\" href=\"tel:+375296713971\">+375 29 671-39-71</a></p></div></div><p class=\"ev-belarus-legal__note\">Информационный сайт EVERSENSE в Республике Беларусь.</p></section>"+'</body>')
 dest.write_text(h,encoding='utf-8')
 return {'url':url,'path':str(dest),'status':'saved','bytes':len(h.encode('utf8')),'asset_replacements':replacements}

# Russian pages before English for faster early feedback; 65 original pages maximum.
pages=AUDIT['pages'];pages=sorted(pages,key=lambda p:('/catalog-en' in p['url'],len(p['url'])))
page_results=[]
with ThreadPoolExecutor(max_workers=8) as pool:
 futures=[pool.submit(rewrite_page,p) for p in pages]
 for n,f in enumerate(as_completed(futures),1):
  x=f.result();page_results.append(x)
  if n%10==0:print('PAGES',n,'saved',sum(x['status']=='saved' for x in page_results),flush=True)

# Keep metadata/manifests, link original media, and explicitly report missing sources.
counts=Counter(x['status'] for x in results)
types=Counter(x.get('type',ext_for(x['url'])) for x in results if x['status'] in ('saved','cached'))
fail=[x for x in results if x['status']=='missing']
video=[x for x in results if ext_for(x['url']) in ('mp4','webm')]
summary={'source':'https://ever-home.ru/','captured_page_count':len(pages),'pages_saved':sum(p['status']=='saved' for p in page_results),'asset_total':len(results),'asset_status':dict(counts),'asset_types':dict(types),'total_saved_bytes':sum(x.get('bytes',0) for x in results),'video_results':video,'missing_assets':fail,'missing_pages':[x for x in page_results if x['status']!='saved']}
(ROOT/'reference/original-media-manifest.json').write_text(json.dumps({'summary':summary,'files':results,'pages':page_results},ensure_ascii=False,indent=2),encoding='utf8')
lines=['# Доступность оригинальных материалов EVERSENSE','',f"Страниц скопировано: **{summary['pages_saved']}/{summary['captured_page_count']}**.",f"Ресурсов локально сохранено: **{counts['saved']+counts['cached']}/{len(results)}**.",f"Объём сохранённых ресурсов: **{summary['total_saved_bytes']/1024/1024:.1f} МБ**.",'','## Видео']
for v in video:lines.append('- '+str(v['status'])+' · '+v['url']+((' — '+str(v.get('error'))) if v.get('error') else ''))
lines.extend(['','## Недоступные файлы',''])
for v in fail:lines.append('- '+v['url']+' · '+str(v.get('error')))
lines.extend(['','## Недостающие материалы, которые нельзя восстановить из публичной версии','', '- Исходные несжатые фотографии интерьеров и текстур, если на Tilda опубликованы только уменьшенные JPEG.','- Оригинальные проектные файлы Zero Block, если часть анимаций загружается из внутренней админки Tilda.','- Финальные цены BYN, актуальные адреса дилеров в Беларуси, список укладчиков и официальные условия гарантии для рынка РБ.','- Реальные проекты заказчиков и фотографии их объектов, которых нет на публичном сайте производителя.'])
(ROOT/'reference/missing-media.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('MIRROR_SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ('missing_assets','missing_pages','video_results')},ensure_ascii=False),flush=True)
print('VIDEOS',json.dumps(video,ensure_ascii=False),flush=True)
print('MISSING_FIRST',json.dumps(fail[:12],ensure_ascii=False),flush=True)