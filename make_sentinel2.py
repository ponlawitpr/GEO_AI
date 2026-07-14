"""
สร้าง sentinel2.html : ภาพ Sentinel-2 ประเทศไทย ปี 2026 (ต้นปี -> ปัจจุบัน)
แบบ median ปลอดเมฆ (Cloud Score+) วางทับพื้นหลัง Google Satellite
ไฟล์ผลลัพธ์เปิดได้ด้วยการดับเบิลคลิก (ไม่ต้องรัน server / ไม่ต้อง API key)

วิธีใช้:
    1) ล็อกอินครั้งเดียว:  earthengine authenticate
    2) รัน:                python make_sentinel2.py
"""
import datetime
import ee
import folium

PROJECT = "ponlawit-pryurachatuporn"
START = "2026-01-01"
# filterDate ปลายทางเป็น exclusive -> +1 วัน เพื่อรวมภาพของวันนี้ด้วย
END = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
CLEAR_THRESHOLD = 0.60  # cs_cdf : ยิ่งสูงยิ่งเข้มงวดเรื่องเมฆ (0-1)

print(f"Initializing Earth Engine (project={PROJECT}) ...")
ee.Initialize(project=PROJECT)

# 1) ขอบเขตประเทศไทย
thailand = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(
    ee.Filter.eq("ADM0_NAME", "Thailand")
)

# 2) Cloud Score+ สำหรับ mask เมฆ (แม่นกว่า QA60)
cs_plus = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
QA_BAND = "cs_cdf"

# 3) Sentinel-2 SR + กรองเวลา/ขอบเขต + mask เมฆ
s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(thailand)
    .filterDate(START, END)
    .linkCollection(cs_plus, [QA_BAND])
    .map(lambda img: img.updateMask(img.select(QA_BAND).gte(CLEAR_THRESHOLD)))
)

count = s2.size().getInfo()
print(f"พบภาพ Sentinel-2 ในช่วง {START} -> {END} : {count} ภาพ")

# 4) median composite + clip ขอบเขตไทย
composite = s2.median().clip(thailand)
vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.1}

# เส้นขอบประเทศไทย (สีเหลือง)
outline = ee.Image().paint(featureCollection=thailand, color=1, width=2)

# 5) ดึง tile URL จาก Earth Engine
print("ขอ tile จาก Earth Engine ...")
s2_url = composite.getMapId(vis)["tile_fetcher"].url_format
outline_url = outline.getMapId({"palette": "FFFF00"})["tile_fetcher"].url_format

# 6) สร้างแผนที่ folium + พื้นหลัง Google Satellite
m = folium.Map(location=[13.2, 101.0], zoom_start=6, tiles=None, control_scale=True)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google", name="Google Satellite", overlay=False, control=True,
    max_zoom=20,
).add_to(m)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attr="Google", name="Google Hybrid (มีชื่อสถานที่)", overlay=False, control=True,
    max_zoom=20,
).add_to(m)

folium.TileLayer(
    tiles=s2_url, attr="Google Earth Engine",
    name="Sentinel-2 median 2026 (ปลอดเมฆ)", overlay=True, control=True,
).add_to(m)

folium.TileLayer(
    tiles=outline_url, attr="Google Earth Engine",
    name="ขอบเขตประเทศไทย", overlay=True, control=True,
).add_to(m)

# กล่องข้อมูลมุมบนซ้าย
title_html = f"""
<div style="position: fixed; top: 12px; left: 60px; z-index: 9999;
     background: rgba(255,255,255,.95); padding: 8px 14px; border-radius: 8px;
     box-shadow: 0 2px 10px rgba(0,0,0,.25); font-family: 'Segoe UI',Tahoma,sans-serif;">
  <b style="color:#1a3d5c;">🛰️ Sentinel-2 ประเทศไทย 2026</b><br>
  <span style="font-size:12px;color:#5a6b7a;">Median ปลอดเมฆ · {START} → {END} · ภาพจริง B4/B3/B2</span>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

folium.LayerControl(collapsed=False).add_to(m)

OUT = "sentinel2.html"
m.save(OUT)
print(f"เสร็จ! เขียนไฟล์ {OUT} แล้ว — ดับเบิลคลิกเปิดได้เลย")
