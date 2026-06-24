import logging
from typing import Optional

import httpx

from app.config.settings import settings

from app.clients.mock_data import mocked_fornecedor_exists

logger = logging.getLogger(__name__)

def supplier_exists(supplier_id: str, bearer_token: Optional[str] = None) -> Optional[bool]:
    """Verifica se `supplier_id` existe no MS de Fornecedores."""
    if not settings.SUPPLIER_SERVICE_URL:
        # Sem o MS de Fornecedores real configurado: valida contra a lista
        # mockada (formato autorizado pelo professor), em vez de pular.
        return mocked_fornecedor_exists(supplier_id)

    if not supplier_id or not isinstance(supplier_id, str):
        return False

    url = f"{settings.SUPPLIER_SERVICE_URL.rstrip('/')}/suppliers/{supplier_id}"
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
            supplier_id,
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
        supplier_id,
    )
    return None
