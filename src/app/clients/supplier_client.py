import logging
from typing import Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Cliente HTTP para validar, de forma cross-service, se um fornecedorId
# informado em um Produto corresponde a um fornecedor existente no
# chave-ms-supplier (MS de Fornecedores).
#
# Mesma decisão de trade-off adotada em categoria_client.py: fail-open em
# caso de indisponibilidade da rede/serviço (ver ADR.md, seção 6.2).
# Bloqueante (400) apenas quando o serviço CONFIRMA (404) que o fornecedor
# não existe.
#
# Diferença em relação à Categoria: o ID de Fornecedor já é uma string
# (UUID), então não há conversão/validação de formato numérico aqui.


def fornecedor_exists(fornecedor_id: str, bearer_token: Optional[str] = None) -> Optional[bool]:
    """Verifica se `fornecedor_id` existe no MS de Fornecedores.

    Retorna:
        True  -> fornecedor existe
        False -> fornecedor não existe (404 confirmado pelo serviço)
        None  -> não foi possível confirmar (serviço não configurado,
                 indisponível ou demorou demais) — fail-open: o chamador
                 não deve bloquear a operação.
    """
    if not settings.SUPPLIER_SERVICE_URL:
        return None

    url = f"{settings.SUPPLIER_SERVICE_URL.rstrip('/')}/suppliers/{fornecedor_id}"
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    try:
        response = httpx.get(
            url,
            headers=headers,
            timeout=settings.SUPPLIER_SERVICE_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Não foi possível validar fornecedorId=%s no MS de Fornecedores (%s). "
            "Seguindo sem bloquear a operação (fail-open).",
            fornecedor_id,
            exc,
        )
        return None

    if response.status_code == 404:
        return False

    if response.status_code == 200:
        return True

    logger.warning(
        "Resposta inesperada (status=%s) do MS de Fornecedores ao validar fornecedorId=%s.",
        response.status_code,
        fornecedor_id,
    )
    return None
