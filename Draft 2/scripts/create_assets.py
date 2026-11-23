"""Original Dormie SVG pixel artwork, reproducible with Python standard library."""
from pathlib import Path
import random
OUT = Path(__file__).resolve().parents[1] / 'app/static/assets'
OUT.mkdir(parents=True, exist_ok=True)

def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" shape-rendering="crispEdges">{body}</svg>'

def rect(x,y,w,h,c):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>'

def path(d,c):
    return f'<path d="{d}" fill="{c}"/>'

# Four full-body, neutral casual-clothing sprites in a consistent original style.
for i, (skin, hair, coat, shade, pants) in enumerate([
    ('#e7ae79','#493027','#697044','#454d35','#45413c'),
    ('#bc875d','#322c29','#e0c8a0','#ad926f','#75654c'),
    ('#d59b69','#382c25','#c39a50','#8c683e','#444c47'),
    ('#bd8259','#422d25','#71805a','#495b43','#c3ae8a')]):
    b = ''
    # silhouette / chunky pixel outline
    b += path('M24 6h18v4h7v7h4v19h-5v9h-5v5h8v6h5v38h-6v7h-3v29h4v8H31v-7h-2v7H9v-8h4v-29H8v-8H4V59h5v-8h11v-7h-6v-9h-4V19h5v-8h9z','#342a23')
    if i == 1:
        b += path('M17 12h27v7h7v41h-8V42H18v18H9V22h8z',hair)
    b += rect(18,20,27,22,skin)+rect(23,39,16,10,skin)
    b += rect(19,34,4,5,'#d08e64')+rect(40,34,4,5,'#d08e64')
    b += rect(24,27,3,5,'#342a23')+rect(37,27,3,5,'#342a23')+rect(30,37,7,2,'#a55c43')
    b += path('M17 13h7V8h16v5h7v8h-5v-4h-7v6h-8v-4h-6v6h-6z',hair)
    b += rect(24,11,8,3,'#6f4932')+rect(38,15,5,3,'#6f4932')
    if i == 2:
        b += path('M20 25h12v2h3v-2h11v10H35v-6h-3v6H20z','#342a23')+rect(22,27,8,6,skin)+rect(37,27,7,6,skin)+rect(25,28,2,4,'#302c27')+rect(39,28,2,4,'#302c27')
    if i == 3:
        b += path('M17 11h24v5h7v8H15v-7h2z','#b8aa7d')+rect(37,21,17,4,'#817953')+rect(25,14,8,4,'#7b7752')
    b += path('M17 49h9l6 5 7-5h7v7h6v30h-6v10H13V85H8V60h5v-7h4z',coat)
    b += path('M24 46h16l4 5-9 10h-7L18 51z','#f0dfbd')+rect(28,57,9,34,'#dfc9a1')+rect(30,62,5,2,'#ac926c')+rect(30,70,5,2,'#ac926c')
    b += rect(12,60,5,23,shade)+rect(43,59,5,26,shade)+rect(18,72,8,9,shade)+rect(39,72,7,9,shade)
    b += rect(12,87,7,8,skin)+rect(44,87,6,8,skin)+rect(21,57,2,11,'#a08d66')+rect(40,57,2,11,'#a08d66')
    b += path('M17 96h27v30H33v-22h-5v22H17z',pants)+rect(17,104,6,10,shade)+rect(39,104,5,10,shade)
    b += rect(16,125,12,6,'#bca487')+rect(33,125,13,6,'#bca487')+rect(12,131,16,4,'#f4e6cb')+rect(33,131,17,4,'#f4e6cb')
    b += rect(18,127,9,2,'#f4e6cb')+rect(35,127,9,2,'#f4e6cb')
    OUT.joinpath(f'resident-{i}.svg').write_text(svg(64,142,b))

# Room rendered on a low-resolution pixel grid with deterministic texture.
rng = random.Random(187)
b=rect(0,0,480,290,'#d8b58a')
for y in range(0,180,12):
    for x in range(0,480,12):
        b+=rect(x,y,12,12,rng.choice(['#d8b58a','#d5b186','#dbb990','#d7b38a']))
b+=rect(0,178,480,112,'#bb885f')
for y in range(180,290,14):
    b+=rect(0,y,480,2,'#956746')+rect(0,y+2,480,2,'#d5a276')
    for x in range((y%3)*25,480,74):b+=rect(x,y,2,14,'#a4724f')
# timber
for x in [4,110,364,470]:b+=rect(x,0,7,184,'#8d623e')+rect(x+1,0,2,181,'#b58859')
b+=rect(0,0,480,9,'#694b34')+rect(0,9,480,4,'#aa7a4d')+rect(0,173,480,6,'#8d623e')
# window trees/clouds
b+=rect(164,23,154,109,'#78583c')+rect(169,28,144,96,'#a7c6c4')
for x,y in [(175,45),(234,36),(280,55)]:
    b+=path(f'M{x} {y}h8v-5h15v5h8v8h-31z','#f6e8cb')
for x,y in [(170,80),(205,92),(260,78),(293,91)]:
    b+=rect(x+8,y+8,4,38,'#8c7549')+path(f'M{x} {y}h8v-7h17v7h8v20h-8v6h-17v-6h-8z','#7f9655')+rect(x+4,y,15,9,'#a4b369')
for x in [169,216,264,310]:b+=rect(x,28,4,99,'#8b6743')
b+=rect(169,73,144,5,'#8b6743')+rect(159,129,166,6,'#ae7b4b')
# beds on both edges
for x in [-8,410]:
    b+=rect(x,56,74,139,'#64472e')+rect(x+4,60,66,129,'#a67546')
    for y in [85,148]:
        b+=rect(x+5,y,62,16,'#ece0c5')+rect(x+28,y+3,39,13,'#a6a18c')+rect(x+28,y+6,39,3,'#c9c2a6')+rect(x+7,y-2,19,9,'#fff1d4')+rect(x+4,y+16,66,7,'#865934')
    for xx in [x+1,x+67]:b+=rect(xx,52,6,150,'#78502e')+rect(xx+1,53,2,148,'#ba8950')
    b+=rect(x+49,69,4,127,'#62462d')
    for y in range(76,196,18):b+=rect(x+47,y,17,3,'#9b6f40')
# bookcases
for x in [74,335]:
    b+=rect(x,112,47,71,'#775237')+rect(x+4,116,39,63,'#513e2d')
    for y in [119,147]:
        for xx in range(x+6,x+41,6):
            hh=rng.randrange(14,24)
            b+=rect(xx,y+24-hh,4,hh,rng.choice(['#7a855c','#d1b17c','#9c6f4d','#a3aaa0']))+rect(xx,y+25-hh,4,2,'#dfcba6')
        b+=rect(x,y+24,47,4,'#ac7c4b')
# corkboard and wall art
b+=rect(127,39,26,39,'#795738')+rect(130,42,20,33,'#ede0b5')+rect(135,49,10,13,'#80946a')+rect(138,54,4,12,'#c5ac77')
b+=rect(331,35,29,48,'#8e603b')+rect(334,38,23,42,'#b19060')+rect(338,45,16,9,'#efdfbc')+rect(336,61,11,12,'#dfc89d')
# rug
b+=path('M126 205h230l44 60H79z','#897c4c')+path('M132 209h218l38 51H91z','#d7c497')+path('M136 213h210l31 42H102z','#a8a071')
for x in range(116,365,12): b+=rect(x,250,5,2,'#c5b88c')
# potted plants
for x,y in [(86,98),(345,98),(131,156),(320,158),(26,233),(441,237)]:
    b+=rect(x,y,15,4,'#90613c')+rect(x+2,y+4,11,15,'#b78b53')+rect(x+4,y+4,3,13,'#cca06a')
    b+=rect(x+7,y-22,2,24,'#586a3d')
    for dx,dy in [(-6,-12),(4,-20),(-4,-25),(5,-6)]:
        b+=path(f'M{x+dx} {y+dy}h8v-3h5v9h-5v3h-8z','#647c43')+rect(x+dx+2,y+dy,6,3,'#95a35c')
# pendant
b+=rect(238,9,2,11,'#68503a')+path('M230 20h19v4h5v5h-29v-5h5z','#b7894c')+rect(228,29,24,3,'#f0d295')
# foreground tables
b+=rect(0,270,71,9,'#8c603c')+rect(0,266,74,5,'#c49663')+rect(424,270,56,20,'#805937')+rect(420,266,60,6,'#bb8e58')
OUT.joinpath('dorm-room.svg').write_text(svg(480,290,b))
# isometric dorm vignette, a separate illustration built from original primitives
b=path('M20 109L178 30l158 79v132l-158 80L20 241z','#73583e')+path('M20 109L178 30v137L20 241z','#dcc4a0')+path('M178 30l158 79v132l-158-74z','#cdb18a')+path('M20 241l158-74 158 74-158 80z','#be9062')
for y in range(180,290,16): b+=path(f'M{20+(y-180)*1.4} {241+(y-180)*.5}l145-70 3 2-145 70z','#d6ae7f')
b+=path('M208 63l83 42v65l-83-42z','#72573c')+path('M214 72l71 36v50l-71-36z','#a0c2bc')+path('M245 88l5 2v51l-5-2z','#72573c')
b+=path('M35 131l74-37 53 26-74 37z','#eee1bf')+path('M35 131v58l53 27v-59z','#a9774b')+path('M88 157l74-37v59l-74 37z','#8d6746')
b+=path('M38 126l71-35 47 24-71 35z','#a4aa89')+path('M40 124l23-12 45 23-23 12z','#f7e8cc')
b+=path('M121 217l74-37 53 26-74 37z','#7c8b50')+path('M121 217v26l53 27v-27z','#596841')+path('M174 243l74-37v26l-74 38z','#6b7b4a')
b+=path('M222 245l42-21 42 21-42 21z','#dcaf70')+path('M222 245v7l42 21v-7z','#956b43')+path('M264 266l42-21v7l-42 21z','#785735')
b+=rect(264,198,3,29,'#566b38')+path('M251 206h13v-14h10v13h12v9h-14v12h-10v-12h-11z','#6f8845')
OUT.joinpath('welcome-room.svg').write_text(svg(356,340,b))
OUT.joinpath('house.svg').write_text(svg(32,32,path('M14 2h4v4h4v4h4v4h4v5h-4v11H6V19H2v-5h4v-4h4V6h4z','#58783d')+path('M14 9h4v4h4v5h1v9H9v-9h1v-5h4z','#f1dfad')+rect(15,20,5,7,'#8c703b')+rect(10,19,3,4,'#a29a4f')))
