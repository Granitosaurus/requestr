from requestr import Response
import pytest

def test_response_init():
    # example json response
    resp = Response("http://httpbin.org", 200, content=b'{"foo": "bar"}', headers={"Content-Type": "application/json"})
    assert resp.status == 200
    assert resp.url == "http://httpbin.org"
    assert resp.text == '{"foo": "bar"}'
    assert resp.json == {"foo": "bar"}

def test_encoding():
    resp = Response("http://httpbin.org", 200, content=b'foobar', headers={"Content-Type": "application/json"}, encoding="utf-8")
    assert resp.url 
    assert resp.text == "foobar"


def test_invalid_json_response():
    # no application headers
    resp = Response("http://httpbin.org", 200, content=b'{"foo": "bar"}')
    with pytest.raises(ValueError):
        assert resp.json
