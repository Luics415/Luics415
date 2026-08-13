#!/usr/bin/env python3
import urllib.request, json, os, math
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

USER=os.getenv("PROFILE_USER","Luics415")
OUT=Path(os.getenv("PROFILE_ASSETS","assets")); OUT.mkdir(parents=True,exist_ok=True)
C={"bg":"#08111F","panel":"#101C31","powder":"#A6D0F2","wine":"#A84370","text":"#F3F7FF","muted":"#A7B7D0","border":"#314665"}
def rgb(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
BG,PANEL,POWDER,WINE,TXT,MUTED,BORDER=[rgb(C[k]) for k in ("bg","panel","powder","wine","text","muted","border")]
def F(s,b=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p,s)
def api(path):
    h={"Accept":"application/vnd.github+json","User-Agent":"Luics415-profile-generator"}
    if os.getenv("GH_TOKEN"): h["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com"+path,headers=h),timeout=30) as r:
        return json.load(r)
def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

repos=api(f"/users/{USER}/repos?per_page=100&sort=updated")
exclude={USER.lower(),"curriculum","mediapipe"}
repos=[r for r in repos if not r.get("fork") and not r.get("archived") and r["name"].lower() not in exclude]

totals={}; repo_lang={}
for r in repos:
    try: ls=api(f"/repos/{USER}/{r['name']}/languages")
    except Exception: ls={}
    repo_lang[r["name"]]=ls
    for n,v in ls.items(): totals[n]=totals.get(n,0)+v

# STACK — top 12, 6 visible in SVG, 6+6 in GIF
total=sum(totals.values()) or 1
langs=[n for n,_ in sorted(totals.items(),key=lambda kv:kv[1],reverse=True)[:12]]
fallback=["C#","C","C++","Java","Python","PHP","Kotlin","JavaScript","TypeScript","HTML","CSS","Sass"]
for n in fallback:
    if n not in langs: langs.append(n)
    if len(langs)>=12: break

cards=[]
for i,n in enumerate(langs[:6]):
    r,c=divmod(i,3); x=48+c*301; y=96+r*119; a=C["powder"] if i%2==0 else C["wine"]
    pct=totals.get(n,0)/total*100
    cards.append(f'<g transform="translate({x} {y})"><rect width="274" height="96" rx="18" fill="{C["panel"]}" stroke="{a}" stroke-width="2"/><rect x="15" y="15" width="12" height="66" rx="6" fill="{a}"/><text x="46" y="39" fill="{C["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="700">{esc(n)}</text><text x="46" y="67" fill="{C["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="11">{pct:.1f}% del código detectado</text></g>')
(OUT/"stack.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="355" viewBox="0 0 1000 355"><rect x="1" y="1" width="998" height="353" rx="26" fill="{C["bg"]}" stroke="{C["border"]}"/><text x="48" y="43" fill="{C["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="21" font-weight="700">STACK // REPOSITORY SIGNAL</text><text x="48" y="69" fill="{C["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="13">Datos agregados desde los repositorios públicos de @{USER}.</text>{"".join(cards)}</svg>',encoding="utf-8")

def stackpage(items,idx):
    im=Image.new("RGB",(1000,355),BG); d=ImageDraw.Draw(im)
    d.rounded_rectangle((1,1,998,353),26,fill=BG,outline=BORDER)
    d.text((48,24),"STACK // REPOSITORY SIGNAL",font=F(21,True),fill=TXT)
    d.text((48,55),f"Carrusel {idx+1}/2 · {len(repos)} repositorios analizados",font=F(13),fill=MUTED)
    for i,n in enumerate(items):
        r,c=divmod(i,3); x=48+c*301; y=96+r*119; a=POWDER if i%2==0 else WINE
        d.rounded_rectangle((x,y,x+274,y+96),18,fill=PANEL,outline=a,width=2)
        d.rounded_rectangle((x+15,y+15,x+27,y+81),6,fill=a)
        pct=totals.get(n,0)/total*100
        d.text((x+46,y+23),n,font=F(18,True),fill=TXT); d.text((x+46,y+57),f"{pct:.1f}% del código",font=F(11),fill=MUTED)
    return im
frames=[stackpage(langs[:6],0) for _ in range(20)]+[stackpage(langs[6:12],1) for _ in range(20)]
frames[0].save(OUT/"stack.gif",save_all=True,append_images=frames[1:],duration=140,loop=0,optimize=True)

# PROJECTS — automatic score
now=datetime.now(timezone.utc)
def score(r):
    pushed=datetime.fromisoformat(r["pushed_at"].replace("Z","+00:00"))
    age=max(0,(now-pushed).days)
    return max(0,180-age)*2 + min(130,math.log10(max(1,r.get("size",1)))*32) + (30 if r.get("description") else 0) + min(50,r.get("stargazers_count",0)*10)
prs=[r for r in repos if r.get("size",0)>1]
prs.sort(key=score,reverse=True); prs=prs[:6]
items=[]
for r in prs:
    ls=repo_lang.get(r["name"],{})
    lang=max(ls,key=ls.get) if ls else (r.get("language") or "Repository")
    items.append((r["name"],lang,(r.get("description") or "Repositorio de desarrollo de software").strip()))

cards=[]
for i,(n,l,dsc) in enumerate(items):
    rr,cc=divmod(i,3); x=48+cc*301; y=95+rr*122; a=C["powder"] if i%2==0 else C["wine"]
    short=dsc if len(dsc)<=45 else dsc[:42]+"..."
    cards.append(f'<g transform="translate({x} {y})"><rect width="274" height="101" rx="18" fill="{C["panel"]}" stroke="{C["border"]}"/><rect width="274" height="5" rx="3" fill="{a}"/><text x="18" y="30" fill="{a}" font-family="Segoe UI,Arial,sans-serif" font-size="10">{esc(l.upper())}</text><text x="18" y="55" fill="{C["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="700">{esc(n[:30])}</text><text x="18" y="79" fill="{C["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="10">{esc(short)}</text></g>')
(OUT/"projects.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360"><rect x="1" y="1" width="998" height="358" rx="26" fill="{C["bg"]}" stroke="{C["border"]}"/><text x="48" y="43" fill="{C["text"]}" font-family="Segoe UI,Arial,sans-serif" font-size="21" font-weight="700">FEATURED PROJECTS // AUTO-SYNC</text><text x="48" y="69" fill="{C["muted"]}" font-family="Segoe UI,Arial,sans-serif" font-size="13">Selección automática basada en actividad, contenido y relevancia.</text>{"".join(cards)}</svg>',encoding="utf-8")

frames=[]
for k in range(22):
    im=Image.new("RGB",(1000,360),BG); d=ImageDraw.Draw(im)
    d.rounded_rectangle((1,1,998,358),26,fill=BG,outline=BORDER)
    d.text((48,24),"FEATURED PROJECTS // AUTO-SYNC",font=F(21,True),fill=TXT)
    d.text((48,55),f"{len(repos)} repositorios públicos analizados",font=F(13),fill=MUTED)
    for i,(n,l,dsc) in enumerate(items):
        rr,cc=divmod(i,3); x=48+cc*301; y=95+rr*122; a=POWDER if i%2==0 else WINE
        d.rounded_rectangle((x,y,x+274,y+101),18,fill=PANEL,outline=BORDER)
        d.rounded_rectangle((x,y,x+274,y+5),3,fill=a)
        d.text((x+18,y+18),l.upper(),font=F(10,True),fill=a); d.text((x+18,y+43),n[:30],font=F(14,True),fill=TXT)
        short=dsc if len(dsc)<=47 else dsc[:44]+"..."
        d.text((x+18,y+69),short,font=F(10),fill=MUTED)
    frames.append(im)
frames[0].save(OUT/"projects.gif",save_all=True,append_images=frames[1:],duration=110,loop=0,optimize=True)
print("Dynamic stack/projects refreshed.")
