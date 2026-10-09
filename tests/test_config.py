from config import config

def test_config_defaults():
    assert config.GITHUB_BRANCH == "main" or isinstance(config.GITHUB_BRANCH, str)
    assert isinstance(config.SECRET_KEY, str)

def test_config_validation():
    validation = config.validate(check_github=False, check_ai=False)
    assert "valid" in validation
    assert "missing" in validation
