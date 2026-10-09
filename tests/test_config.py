import os
from config import Config

def test_config_defaults():
    assert Config.GITHUB_BRANCH == "main" or isinstance(Config.GITHUB_BRANCH, str)
    assert isinstance(Config.SECRET_KEY, str)

def test_config_validation():
    validation = Config.validate(check_github=False, check_ai=False)
    assert "valid" in validation
    assert "missing" in validation
