from requestr.proxy import ProxyPool
import random


def test_ProxyPool():
    random.seed(0)
    pool = ProxyPool([1,2,3,4])
    assert pool.random == 4
    assert pool.random == 2
    assert pool.random == 1
    assert pool.random == 3
    # pool refresh
    assert pool.random == 3