from src import config


def test_ambiente_vence_arquivo_e_arquivo_vence_padrao(tmp_path, monkeypatch):
    (tmp_path / "c.env").write_text('GROOV_CIDADE="Recife"\n# GROOV_LAT=1\nGROOV_LON=-34.9\r\n', encoding="utf-8")
    monkeypatch.setattr(config, "ENV", tmp_path / "c.env")
    assert config.valor("GROOV_CIDADE") == "Recife" and config.valor("GROOV_LAT", "x") == "x"
    assert config.valor("GROOV_LON") == "-34.9"
    monkeypatch.setenv("GROOV_CIDADE", "Natal")
    assert config.valor("GROOV_CIDADE") == "Natal"


def test_arquivo_ausente_usa_padrao():
    assert config.valor("GROOV_MAR", "p") == "p"


def test_lista_separa_por_virgula(monkeypatch):
    monkeypatch.setenv("GROOV_FRASES_EXTRA", " acorda assistente, ,assistente acorda ")
    assert config.lista("GROOV_FRASES_EXTRA") == ["acorda assistente", "assistente acorda"]


def test_apresentar_usuario(monkeypatch):
    assert config.apresentar_usuario() == ""
    monkeypatch.setenv("GROOV_NOME_USUARIO", "Ana")
    assert config.apresentar_usuario() == "O usuário se chama Ana."


def test_os_testes_nao_leem_o_env_real():
    assert config.ENV.name == "sem.env" and not config.ENV.exists()
