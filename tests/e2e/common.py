import pytest
import os


@pytest.fixture
def test_path():
    path = os.path.abspath(__file__)
    return os.path.dirname(path)
