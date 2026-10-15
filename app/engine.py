"""Typed, auditable spatial workflow. Coordinates are synthetic WGS84 fixtures."""
import re
import time
from uuid import uuid4

from pydantic import BaseModel, Field
from pyproj import Transformer
from shapely.geometry import Point, Polygon, mapping
from shapely import transform as transform_geometry


def transform(projector, geometry):
    return transform_geometry(geometry, projector, interleaved=False)

PROJECT = Transformer.from_crs('EPSG:4326', 'EPSG:32651', always_xy=True).transform
UNPROJECT = Transformer.from_crs('EPSG:32651', 'EPSG:4326', always_xy=True).transform


class Constraints(BaseModel):
    max_metro_m: int = Field(default=800, ge=100, le=3000)
    max_rent: int = Field(default=20000, ge=1000, le=100000)
    competitor_radius_m: int = Field(default=500, ge=100, le=2000)
    exclude_risk: bool = True


class Query(BaseModel):
    prompt: str = Field(default='', max_length=1000)
    constraints: Constraints = Field(default_factory=Constraints)
    mode: str = Field(default='multi', pattern='^(multi|single)$')


def fixture():
    shops = [
        ('S01', '滨河创意铺', 121.464, 31.235, 14500),
        ('S02', '静巷转角铺', 121.469, 31.233, 17000),
        ('S03', '书院街沿街铺', 121.475, 31.237, 19000),
        ('S04', '中央商务铺', 121.481, 31.232, 28000),
        ('S05', '东岸社区铺', 121.488, 31.239, 13500),
        ('S06', '南园小铺', 121.478, 31.224, 11000),
        ('S07', '艺术园区铺', 121.459, 31.241, 18500),
        ('S08', '北城街角铺', 121.482, 31.246, 16000),
        ('S09', '西街社区铺', 121.453, 31.229, 12000),
        ('S10', '花园广场铺', 121.472, 31.241, 21500),
        ('S11', '南岸办公铺', 121.487, 31.227, 18000),
        ('S12', '文创集市铺', 121.466, 31.244, 15000),
    ]
    stations = [('M1',121.467,31.235),('M2',121.479,31.234),('M3',121.484,31.244)]
    competitors = [('C1',121.469,31.234),('C2',121.470,31.235),('C3',121.480,31.235),('C4',121.482,31.244),('C5',121.464,31.244)]
    features = []
    for sid, name, lon, lat, rent in shops:
        features.append({'type':'Feature','geometry':mapping(Point(lon,lat)), 'properties':{'id':sid,'name':name,'kind':'site','rent':rent}})
    for kind, records in [('metro',stations),('competitor',competitors)]:
        for sid, lon, lat in records:
            features.append({'type':'Feature','geometry':mapping(Point(lon,lat)), 'properties':{'id':sid,'name':sid,'kind':kind}})
    risk = Polygon([(121.461,31.232),(121.466,31.232),(121.466,31.238),(121.461,31.238)])
    features.append({'type':'Feature','geometry':mapping(risk),'properties':{'id':'R1','name':'模拟积水风险区','kind':'risk'}})
    return {'type':'FeatureCollection','features':features,'source':'Synthetic fixture v1; not real shops, metro stations or hazards.'}


def plan(query: Query):
    constraints = query.constraints.model_copy()
    warnings = []
    text = query.prompt.strip()
    patterns = [('max_metro_m', r'(?:地铁|车站)(?:距离)?\s*(\d+)\s*米'), ('max_rent',r'(?:月租|租金)(?:不超过|最多|上限|低于)?\s*(\d+)\s*元'), ('competitor_radius_m',r'(?:竞品|竞争)(?:半径)?\s*(\d+)\s*米')]
    recognized = False
    for field, pattern in patterns:
        found = re.search(pattern, text)
        if found:
            recognized = True
            values = constraints.model_dump()
            values[field] = int(found.group(1))
            constraints = Constraints(**values)
    if text:
        warnings.append('离线规划仅识别“地铁800米、月租20000元、竞品500米”等明确数值；其他条件未自动执行，请核对约束面板。')
        if not recognized:
            warnings.append('未识别到受支持的数值条件，使用面板约束。')
    return constraints, warnings


def analyze(constraints: Constraints):
    data = fixture()
    stations = [transform(PROJECT,Point(f['geometry']['coordinates'])) for f in data['features'] if f['properties']['kind']=='metro']
    competitors = [transform(PROJECT,Point(f['geometry']['coordinates'])) for f in data['features'] if f['properties']['kind']=='competitor']
    risk = next(f for f in data['features'] if f['properties']['kind']=='risk')
    polygon = transform(PROJECT,Polygon(risk['geometry']['coordinates'][0]))
    results = []
    for feature in data['features']:
        p = feature['properties']
        if p['kind'] != 'site':
            continue
        point = transform(PROJECT,Point(feature['geometry']['coordinates']))
        distance = min(point.distance(station) for station in stations)
        competition = sum(point.distance(c) <= constraints.competitor_radius_m for c in competitors)
        in_risk = polygon.covers(point)
        reasons = []
        if distance > constraints.max_metro_m:
            reasons.append('超出地铁距离')
        if p['rent'] > constraints.max_rent:
            reasons.append('超过月租预算')
        if in_risk and constraints.exclude_risk:
            reasons.append('位于模拟风险区')
        score = round(100 * (.45 * max(0,1-distance/3000) + .35 * max(0,1-p['rent']/100000) + .20/(1+competition)),2)
        results.append({**p,'coordinates':feature['geometry']['coordinates'],'metro_m':round(distance,1),'competitors':competition,'in_risk':in_risk,'eligible':not reasons,'reasons':reasons,'score':score})
    return sorted(results,key=lambda r:(not r['eligible'],-r['score'],r['id']))


def run(query: Query):
    trace = []
    started = time.perf_counter()
    def record(agent, tool, output, since):
        trace.append({'agent':agent,'tool':tool,'status':'completed','duration_ms':round((time.perf_counter()-since)*1000,2),'output':output})
    t = time.perf_counter()
    constraints, warnings = plan(query)
    record('Planner','parse_constraints',constraints.model_dump(),t)
    t = time.perf_counter()
    data = fixture()
    record('DataAgent','load_fixture',{'features':len(data['features']),'source':data['source']},t)
    t = time.perf_counter()
    results = analyze(constraints)
    record('SpatialAgent','project_distance_overlay_rank',{'sites':len(results),'eligible':sum(r['eligible'] for r in results),'crs':'EPSG:32651'},t)
    if query.mode == 'multi':
        t = time.perf_counter()
        for row in results:
            expected = row['metro_m'] <= constraints.max_metro_m + .1 and row['rent'] <= constraints.max_rent and (not constraints.exclude_risk or not row['in_risk'])
            if expected != row['eligible']:
                raise RuntimeError('Spatial result invariant failed')
        if len({r['id'] for r in results}) != len(results):
            raise RuntimeError('Duplicate site id')
        record('Verifier','check_constraints_and_unique_ids',{'checked':len(results),'passed':True},t)
    else:
        trace = [{'agent':'SingleAgent','tool':'plan_load_analyze','status':'completed','output':{'note':'Same tools and planner; independent verifier disabled.'},'duration_ms':round((time.perf_counter()-started)*1000,2)}]
    buffers = []
    for f in data['features']:
        if f['properties']['kind']=='metro':
            buffer = transform(UNPROJECT,transform(PROJECT,Point(f['geometry']['coordinates'])).buffer(constraints.max_metro_m))
            buffers.append({'type':'Feature','geometry':mapping(buffer),'properties':{'kind':'buffer','name':f['properties']['name']}})
    return {'run_id':str(uuid4()),'mode':query.mode,'planner':'deterministic-offline','constraints':constraints.model_dump(),'warnings':warnings,'results':results,'trace':trace,'duration_ms':round((time.perf_counter()-started)*1000,2),'geojson':{**data,'features':data['features']+buffers},'summary':f'共分析 {len(results)} 个模拟铺位，{sum(r["eligible"] for r in results)} 个满足全部硬约束。'}
