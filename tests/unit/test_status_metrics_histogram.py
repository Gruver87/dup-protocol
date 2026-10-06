"""GET /status duration histogram + RocksDB live gauges on /metrics."""

from __future__ import annotations

from observability.metrics import MetricsCollector


def test_observe_status_ms_histogram_and_gauges():
    mc = MetricsCollector()
    mc.observe_status_ms(75)
    mc.observe_status_ms(1500)
    text = mc.render_prometheus(node_id="n1")
    assert "abs_http_status_duration_ms" in text
    assert 'abs_http_status_duration_ms_count{node_id="n1"} 2' in text
    assert "abs_http_status_last_ms" in text
    assert "abs_http_status_max_ms" in text
    assert 'le="100"' in text
    assert 'le="2000"' in text


def test_observe_status_ms_refuses_nan_inf():
    mc = MetricsCollector()
    mc.observe_status_ms(float("nan"))
    mc.observe_status_ms(float("inf"))
    mc.observe_status_ms("bad")
    text = mc.render_prometheus(node_id="n1")
    assert 'abs_http_status_duration_ms_count{node_id="n1"} 0' in text


def test_rocksdb_live_property_gauges_exported():
    mc = MetricsCollector()
    text = mc.render_prometheus(
        node_id="n1",
        rocksdb_tuning={
            "engine": "rocksdb",
            "source": "live",
            "running_compactions": 2,
            "running_flushes": 1,
            "estimate_num_keys": 99,
        },
    )
    assert "abs_rocksdb_running_compactions" in text
    assert 'abs_rocksdb_running_compactions{node_id="n1"} 2' in text
    assert 'abs_rocksdb_running_flushes{node_id="n1"} 1' in text
    assert 'abs_rocksdb_estimate_num_keys{node_id="n1"} 99' in text
