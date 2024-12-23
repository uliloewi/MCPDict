#!/usr/bin/env python3

import json, os, re
from openpyxl import load_workbook
from opencc import OpenCC

curdir = os.path.dirname(__file__)
spath = os.path.join(curdir, "..", "漢字音典字表檔案（長期更新）.xlsx")
tpath = os.path.join(curdir, "output", os.path.basename(__file__).replace(".py", ".json"))

FeatureCollection = {
  "type": "FeatureCollection",
  "features": []
}

n2o_dict = {}

for line in open("tables/data/mulcodechar.dt", encoding="U8"):
	if not line or line[0] == "#": continue
	fs = line.strip().split("-")
	if len(fs) < 2: continue
	n2o_dict[fs[0]] = fs[1]

opencc_s2t = OpenCC("s2t.json")
opencc_t2s = OpenCC("t2s.json")

def s2t(s):
	if not s: return ""
	if type(s) is not str: return s
	s = opencc_s2t.convert(s)\
		.replace("樑","梁")\
		.replace("嶽","岳")\
		.replace("慄", "栗")
	for n, o in n2o_dict.items():
		s = s.replace(n, o)
	return s

def n2o(s):
	if not s: return ""
	for n, o in n2o_dict.items():
		s = s.replace(n, o)
	return s

def o2n(s):
	if not s: return ""
	for n, o in n2o_dict.items():
		s = s.replace(o, n)
	return s

def t2s(s, prepare = False):
	s = o2n(s)
	if prepare:
		return s
	return opencc_t2s.convert(s)

def outdated():
	if not os.path.exists(tpath): return True
	classtime = os.path.getmtime(__file__)
	stime = os.path.getmtime(spath)
	if classtime > stime: stime = classtime
	ttime = os.path.getmtime(tpath)
	return stime > ttime

markers = {1: '꜀', 2: '꜁', 3: '꜂', 4: '꜃', 5: '꜄', 6: '꜅', 7: '꜆', 8: '꜇'}
markers2 = {1: '꜆', 2: '꜆', 3: '꜄', 4: '꜅', 5: '꜂', 6: '꜃', 7: '꜀', 8: '꜁'}
def getTones(tones):
	l = dict()
	t4s = [""] * 6
	for i,ts in enumerate(tones):
		i = i + 1
		index = i
		if not ts: continue
		ts = ts.lower()
		for j,t in enumerate(ts.split(",")):
			if t.startswith("["):
				index = t[1:t.index("]")]
				t = t[t.index("]")+1:]
			if t[0].isdigit() or t[0] == "-":
				n = t.lstrip("012345-")
				v = t[:len(t)-len(n)]
			else:
				n = t
				v = ""
			#334 1 1a 陰平 ꜀
			t8 = i
			t4 = (i+1)//2
			if i == 10:
				t8 = 0
				t4 = 0
			elif i == 9: t4 = 5
			if "," in ts:
				t8 = str(t8) + chr(ord("a") + j)
			if "," in ts or tones[i - 2 if i % 2 == 0 else i]:
				t4s[t4]+="1"
				t4 = str(t4) + chr(ord("a") + len(t4s[t4]) - 1)
			m = markers.get(i, '') if j == 0 else markers2.get(i, '')
			l[str(index)] = (v,str(t8),str(t4),n,m)
	return json.dumps(l, ensure_ascii=False).lower()

def normNames(s):
	if not s or s == "Web": return ""
	return re.sub(" ?[、，,&] ?", ",", s)

def normJW(s):
	if s:
		s = s.replace(" ", "").replace("，",",").strip()
		jd, wd = map(float, s.split(","))
		s = f"{jd:.6f},{wd:.6f}"
	return s

def getMarkerSize(size):
	if size >= 4: return "large"
	if size == 3: return "medium"
	return "small"

def normVer(s):
	if type(s) is str:
		if s == "/": s = None
	else:
		s = s.strftime("%Y-%m-%d") if s else None
	return s

def normSource(books):
	if books.value:
		if books.hyperlink:
			target = books.hyperlink.target
			return f"<a href={target}>{books.value}</a>"
		else:
			return books.value
	return None

def load():
	if not outdated():
		return json.load(open(tpath,encoding="U8"))
	d = dict()
	wb = load_workbook(spath)
	sheet = wb.worksheets[0]
	lineCount = 0
	fields = []
	for row in sheet.rows:
		lineCount += 1
		line = [j.value if j.value else "" for j in row]
		if lineCount == 1: fields = line
		if lineCount <= 2:
			continue
		fs = dict(zip(fields, line))
		文件名 = fs["文件名"]
		if not 文件名 or 文件名.startswith("#"):
			continue
		語言 = n2o(fs["語言"])
		簡稱 = n2o(fs["簡稱"])
		音系 = fs["音系"]
		說明 = fs["說明"]
		繁簡 = fs["繁簡"]
		字表格式 = fs["字表格式"]
		經緯度 = normJW(fs["經緯度"])
		方言島 = fs["方言島"] == "☑"
		作者 = normNames(fs["作者"])
		錄入人 = normNames(fs["錄入人"])
		維護人 = normNames(fs["維護人"])
		推薦人 = normNames(fs["推薦人"])
		來源 = normSource(row[fields.index("來源")])
		參考文獻 = fs["參考文獻"]
		版本 = normVer(fs["版本/更新時間"])
		跳過行數 = int(fs["跳過行數"]) if fs["跳過行數"] else 0
		地圖級別 = fs["地圖級別"].count("★") if fs["地圖級別"] else 0

		j = fields.index("[1]陰平")
		聲調 = getTones([fs[fields[i]] for i in range(j, j+10)])

		orders = [fs[i] for i in ("地圖集二排序", "音典排序", "陳邡排序")]
		colors = [row[fields.index(i)].fill.fgColor.value[2:] for i in ("地圖集二顏色", "音典顏色","陳邡顏色")]
		subcolor = row[fields.index("音典過渡色")].fill.fgColor.value[2:]
		if subcolor and subcolor != "000000" and subcolor != colors[1]:
				colors[1] += f",{subcolor}"
		colors = [re.sub(r"(\w+)", "#\\1", i) for i in colors]

		types = [fs[i] for i in ("地圖集二分區", "音典分區", "下拉1，折疊分区")]
		if types[2] and fs["下拉2"]: types[2] += "," + fs["下拉2"]
		types[2] = s2t(types[2])

		places = [fs[i] if fs[i] else "" for i in ("省/自治區/直轄市","地區/市/州","縣/市/區","鄕/鎭/街道","村/社區/居民點")]
		地點 = ("".join(places)).replace("/", "")
		行政區級別 = fs["行政區級別"]
		if not 行政區級別:
			行政區級別 = "省會,地級" if fs["省會"] == "☑" else ""
		if not 行政區級別:
			n = 5 - places.count("")
			if n == 1:
				行政區級別 = "省級"
			elif n == 2:
				行政區級別 = "地級"
			elif n == 3:
				行政區級別 = "縣級"
			elif n == 4:
				行政區級別 = "鄕級"
			elif n == 5:
				行政區級別 = "村級"

		d[簡稱] = {
			"序號":row[0].row,
			"語言":語言,
			"簡稱":簡稱,
			"文件名":文件名,
			"文件格式":字表格式,
			"跳過行數":跳過行數,
			"方言島": 方言島,
			"地圖集二排序":orders[0],
			"地圖集二顏色":colors[0],
			"地圖集二分區":types[0],
			"音典排序":orders[1],
			"音典顏色":colors[1],
			"音典分區":types[1],
			"陳邡排序":orders[2],
			"陳邡顏色":colors[2],
			"陳邡分區":types[2],
			"行政區級別": 行政區級別,
			"省":s2t(places[0]).strip("*"),
			"市":places[1],
			"縣":places[2],
			"鎮":places[3],
			"村":places[4],
			"地點": 地點,
			"版本":版本,
			"經緯度":經緯度,
			"地圖級別":str(地圖級別),
			"作者":作者,
			"錄入人":錄入人,
			"維護人":維護人,
			"推薦人":推薦人,
			"來源": 來源,
			"參考文獻":參考文獻,
			"音系":音系,
			"說明":說明,
			"繁簡":繁簡,
			"聲調":聲調
		}
		if not 經緯度: continue
		Feature = {
			"type": "Feature",
			"properties": {
				"marker-color": colors[0],
				"marker-size": getMarkerSize(地圖級別),
				"marker-symbol": orders[0][0].upper() if orders[0] else "",
			},
			"geometry": {
				"type": "Point",
				"coordinates": eval(f"[{經緯度}]")
			}
		}
		for i in ["語言", "地點", "地圖集二分區", "音典分區", "陳邡分區", '方言島', '版本', '作者', '錄入人', '維護人', '來源', '參考文獻', "繁簡"]:
			if d[簡稱][i]:
				Feature["properties"][i] = d[簡稱][i]
		FeatureCollection["features"].append(Feature)
	json.dump(FeatureCollection, fp=open("../方言.geojson","w",encoding="U8",newline="\n"),ensure_ascii=False,indent=2)
	json.dump(d, fp=open(tpath,"w",encoding="U8",newline="\n"),ensure_ascii=False,indent=2)
	return d