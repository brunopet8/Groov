from datetime import datetime
from pathlib import Path

from src.conversa import vault

AGORA = datetime(2026, 11, 13, 18, 33, 42)
PASTAS = ("raw", "wiki", "output", "memoria", "diario")


def test_preparar_cria_estrutura(tmp_path):
    assert vault.preparar(tmp_path) is True
    for p in PASTAS:
        assert (tmp_path / p).is_dir()
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / "wiki" / "_master-index.md").is_file()


def test_preparar_nao_sobrescreve(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("meu", encoding="utf-8")
    vault.preparar(tmp_path)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "meu"


def test_registrar_turno_formato(tmp_path):
    vault.registrar_turno(tmp_path, "VOCÊ", "oi", AGORA)
    texto = (tmp_path / "diario" / "2026-11-13.md").read_text(encoding="utf-8")
    assert texto == "# 2026-11-13\n\n- **18:33:42 VOCÊ:** oi\n"


def test_texto_com_quebra_vira_uma_linha(tmp_path):
    vault.registrar_turno(tmp_path, "GROOV", "a\nb", AGORA)
    vault.registrar_turno(tmp_path, "GROOV", "c", AGORA)
    linhas = (tmp_path / "diario" / "2026-11-13.md").read_text(encoding="utf-8").splitlines()
    assert linhas[2:] == ["- **18:33:42 GROOV:** a b", "- **18:33:42 GROOV:** c"]


def test_arquivo_do_dia_pela_data(tmp_path):
    vault.registrar_turno(tmp_path, "VOCÊ", "x", datetime(2026, 11, 13, 23, 59))
    vault.registrar_turno(tmp_path, "VOCÊ", "y", datetime(2026, 11, 14, 0, 1))
    assert (tmp_path / "diario" / "2026-11-13.md").is_file()
    assert (tmp_path / "diario" / "2026-11-14.md").is_file()


def test_recibo_formato(tmp_path):
    vault.registrar_recibo(tmp_path, "pc", True, 1.25, AGORA)
    vault.registrar_recibo(tmp_path, "clima", True, None, AGORA)
    vault.registrar_recibo(tmp_path, "pc", False, None, AGORA)
    linhas = (tmp_path / "diario" / "2026-11-13.md").read_text(encoding="utf-8").splitlines()
    assert linhas[2:] == ["- 18:33:42 recibo: ferramenta=pc resultado=ok tempo=1,2s",
                          "- 18:33:42 recibo: ferramenta=clima resultado=ok tempo=-",
                          "- 18:33:42 recibo: ferramenta=pc resultado=falhou tempo=-"]


def test_falha_ao_gravar_nao_levanta(tmp_path):
    arquivo = tmp_path / "nao_e_pasta"
    arquivo.write_text("x")
    assert vault.registrar_turno(arquivo, "VOCÊ", "oi", AGORA) is None
    assert vault.preparar(arquivo) is False


def test_raiz_por_variavel(monkeypatch, tmp_path):
    monkeypatch.setenv("GROOV_VAULT", str(tmp_path))
    assert vault.raiz() == tmp_path
    monkeypatch.delenv("GROOV_VAULT")
    assert vault.raiz() == vault.RAIZ_PADRAO


def test_salvar_output_nome_e_texto(tmp_path):
    p = vault.salvar_output(tmp_path, "Vagas de Emprego: semana!", "corpo", AGORA)
    assert p == tmp_path / "output" / "2026-11-13-183342-vagas-de-emprego-semana.md"
    assert p.read_text(encoding="utf-8") == "corpo"


def test_salvar_output_falha_none(tmp_path):
    arquivo = tmp_path / "nao_e_pasta"
    arquivo.write_text("x")
    assert vault.salvar_output(arquivo, "a", "b", AGORA) is None


def test_texto_invalido_nao_levanta(tmp_path):
    assert vault.registrar_turno(tmp_path, "VOCÊ", "\ud800", AGORA) is None


def test_raiz_padrao_mora_no_projeto_e_vem_da_config(tmp_path, monkeypatch):
    from src import config

    monkeypatch.delenv("GROOV_VAULT")  # o conftest aponta o vault para o tmp
    assert vault.RAIZ_PADRAO == Path(vault.__file__).resolve().parents[2] / "vault"
    assert vault.raiz() == vault.RAIZ_PADRAO
    config.ENV.write_text(f"GROOV_VAULT={tmp_path / 'v'}\n", encoding="utf-8")
    assert vault.raiz() == tmp_path / "v"
