"""Contratos de resposta da API (viram tipos TypeScript no app via OpenAPI).

Campos sem dado vêm como `null`, nunca como 0.
"""

from datetime import date, datetime
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RaioKm(IntEnum):
    """Raios pré-calculados no banco (mv_oportunidade_resumo)."""

    KM_25 = 25
    KM_50 = 50
    KM_100 = 100
    KM_250 = 250
    KM_500 = 500


Ordem = Literal["quantidade", "distancia"]
TipoMeta = Literal["coleta_seletiva", "reciclagem", "reducao", "reutilizacao", "eliminacao_lixoes"]


class Modelo(BaseModel):
    model_config = ConfigDict(frozen=True)


class Municipio(Modelo):
    id_ibge: int
    nome: str
    uf: str


class Estabelecimento(Modelo):
    cnpj: str = Field(pattern=r"^\d{14}$")
    razao_social: str
    municipio: Municipio | None


class EstabelecimentoDetalhado(Estabelecimento):
    categoria_atividade: str | None
    detalhe_atividade: str | None


class Residuo(Modelo):
    codigo: str = Field(pattern=r"^\d{6}$")
    descricao: str
    perigoso: bool | None


class ResiduoBusca(Residuo):
    oportunidades: int


class Operacao(Modelo):
    codigo: str
    descricao: str


class Quantidade(Modelo):
    toneladas: float | None
    litros: float | None
    unidades: float | None


class Localizacao(Modelo):
    lat: float
    lon: float
    # Nenhuma fonte tem endereço: a posição é o centróide do município.
    precisao: Literal["municipio"] = "municipio"


class ResumoRotas(Modelo):
    total: int
    distancia_mais_proxima_km: float


class OportunidadeItem(Modelo):
    gerador: Estabelecimento
    residuo: Residuo
    ano: int
    operacoes_atuais: list[Operacao]
    quantidade: Quantidade
    rotas: ResumoRotas
    localizacao: Localizacao


class PaginaOportunidades(Modelo):
    itens: list[OportunidadeItem]
    pagina: int
    por_pagina: int
    total: int
    raio_km: RaioKm


class Meta(Modelo):
    tipo: TipoMeta
    valor_atual: float | None
    valor_meta: float | None
    prazo_texto: str | None
    prazo_ano: int | None
    programa: str | None


class ContextoMunicipal(Modelo):
    ano_referencia: int
    possui_coleta_seletiva: bool
    possui_plano_gestao: bool
    link_plano: str | None
    ano_ultima_versao_plano: int | None
    metas: list[Meta]


class RespostaContexto(Modelo):
    municipio: Municipio
    # null quando o município não tem diagnóstico ("Município sem diagnóstico" no app).
    contexto: ContextoMunicipal | None


class Rota(Modelo):
    destinador: Estabelecimento
    distancia_km: float
    operacoes: list[Operacao]
    ano_mais_recente: int
    quantidade_recebida: Quantidade
    localizacao: Localizacao
    contexto_municipal: ContextoMunicipal | None


class Fonte(Modelo):
    nome: str
    url: str | None
    atualizado_na_fonte: date | None
    importado_em: datetime


class Oportunidade(Modelo):
    gerador: EstabelecimentoDetalhado
    residuo: Residuo
    ano: int
    operacoes_atuais: list[Operacao]
    quantidade: Quantidade
    localizacao: Localizacao


class DetalheOportunidade(Modelo):
    oportunidade: Oportunidade
    raio_km: RaioKm
    rotas: list[Rota]
    fontes: list[Fonte]


class Saude(Modelo):
    status: Literal["ok"]
    banco: Literal["ok"]
    dados_atualizados_em: datetime | None
