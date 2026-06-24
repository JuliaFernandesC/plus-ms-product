import logging
from typing import Optional

import httpx

from app.config.settings import settings

from app.clients.mock_data import mocked_categoria_exists

logger = logging.getLogger(__name__)

# Cliente HTTP para validar, de forma cross-service, se um categoriaId
# informado em um Produto corresponde a uma categoria existente no
# plus-ms-categorias.
#
# DECISÃO: fail-open em caso de indisponibilidade da rede/serviço.
# Se o MS de Categorias estiver fora do ar ou demorar demais para responder,
# preferimos deixar o produto ser criado (e logar um aviso) em vez de
# derrubar a disponibilidade do MS de Produto por causa de uma dependência
# externa. Isso preserva o acoplamento fraco entre os serviços.
# Esse trade-off (consistência vs. disponibilidade) está documentado no
# ADR.md, seção 6.2.
#
# Já se o serviço RESPONDER dizendo que a categoria não existe (404), ou se
# o categoriaId não tiver um formato válido, a validação É bloqueante
# (400 Bad Request) — isso evita produtos "órfãos" apontando para
# categorias inexistentes, sem precisar de uma foreign key física entre
# bancos de dados de serviços diferentes.


def categoria_exists(categoria_id: str, bearer_token: Optional[str] = None) -> Optional[bool]:
    """Verifica se `categoria_id` existe no MS de Categorias.

    Retorna:
        True  -> categoria existe
        False -> categoria não existe (404 confirmado pelo serviço)
        None  -> não foi possível confirmar (serviço não configurado,
                 indisponível ou demorou demais) — o chamador deve tratar
                 isso como "desconhecido" e decidir se segue ou não
                 (aqui, seguimos: fail-open).
    """
    if not settings.CATEGORIA_SERVICE_URL:
        # Sem o MS de Categorias real configurado: valida contra a lista
        # mockada (formato autorizado pelo professor), em vez de pular.
        return mocked_categoria_exists(categoria_id)

    # O MS de Categorias usa IDs numéricos (Long, auto incremento).
    try:
        int(categoria_id)
    except (TypeError, ValueError):
        # Formato claramente inválido: isso não depende de o serviço estar
        # no ar ou não, então tratamos como negativo (bloqueante).
        return False

    url = f"{settings.CATEGORIA_SERVICE_URL.rstrip('/')}/categorias/{categoria_id}"
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    try:
        response = httpx.get(
            url,
            headers=headers,
            timeout=settings.CATEGORIA_SERVICE_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Não foi possível validar categoriaId=%s no MS de Categorias (%s). "
            "Seguindo sem bloquear a operação (fail-open).",
            categoria_id,
            exc,
        )
        return None

    if response.status_code == 404:
        return False

    if response.status_code == 200:
        return True

    # Qualquer outro status (401/403/5xx) é tratado como "desconhecido":
    # não é uma confirmação de inexistência, então não bloqueamos a operação,
    # apenas registramos para investigação.
    logger.warning(
        "Resposta inesperada (status=%s) do MS de Categorias ao validar categoriaId=%s.",
        response.status_code,
        categoria_id,
    )
    return None
