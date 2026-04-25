"""Baseline integration tests using shared test client fixtures."""


def test_root_health_endpoint(test_client) -> None:
    """App-level health endpoint should respond with healthy status."""
    response = test_client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


def test_analysis_stub_health_endpoint(test_client) -> None:
    """Router health endpoint should be mounted for integration test setup."""
    response = test_client.get('/analysis/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
