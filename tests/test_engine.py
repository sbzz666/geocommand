import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point

from app.engine import Constraints, PROJECT, Query, analyze, plan, run, transform
from app.main import app

client = TestClient(app)


def test_distance_is_in_meters():
    a=transform(PROJECT,Point(121.467,31.235))
    b=transform(PROJECT,Point(121.468,31.235))
    assert 90 < a.distance(b) < 100


def test_risk_and_budget():
    rows={r['id']:r for r in analyze(Constraints())}
    assert rows['S01']['in_risk'] and not rows['S01']['eligible']
    assert not rows['S04']['eligible'] and '超过月租预算' in rows['S04']['reasons']
    assert rows['S02']['eligible']


def test_risk_toggle():
    rows={r['id']:r for r in analyze(Constraints(exclude_risk=False))}
    assert rows['S01']['eligible']


def test_prompt_and_unknown_conditions():
    c,w=plan(Query(prompt='地铁500米 月租15000元 竞品300米 必须朝南'))
    assert (c.max_metro_m,c.max_rent,c.competitor_radius_m)==(500,15000,300)
    assert w


def test_modes_same_results_honest_baseline():
    multi=run(Query())
    single=run(Query(mode='single'))
    assert multi['results']==single['results']
    assert len(multi['trace'])==4 and len(single['trace'])==1


def test_empty_result():
    assert not any(r['eligible'] for r in analyze(Constraints(max_rent=1000)))


@pytest.mark.parametrize('body',[{'constraints':{'max_metro_m':-1}},{'mode':'bogus'},{'prompt':'地铁99999米'},{'prompt':'a'*1001}])
def test_invalid_request(body):
    assert client.post('/api/analyze',json=body).status_code==422


def test_api_and_geojson():
    assert client.get('/').status_code==200
    assert client.get('/api/health').json()['status']=='ok'
    result=client.post('/api/analyze',json={}).json()
    assert result['geojson']['type']=='FeatureCollection'
    assert sum(f['properties']['kind']=='buffer' for f in result['geojson']['features'])==3
    assert all(r['score']>=0 for r in result['results'])
    assert len({r['id'] for r in result['results']})==12
