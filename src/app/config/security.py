from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config.settings import settings

# Arquivo responsável pela validação de tokens JWT e pelo controle de acesso
# baseado em papéis (RBAC) dentro do MS de Produto.
#
# Este serviço NÃO emite tokens (isso é responsabilidade exclusiva do
# plus-ms-auth). Aqui apenas REPLICAMOS a lógica de verificação de
# assinatura/expiração usando o mesmo segredo (JWT_SECRET) e o mesmo
# algoritmo (HS256) configurados no MS de Auth — exatamente o mesmo padrão
# adotado pelo plus-ms-categorias (ver HmacSha256JwtDecoder/SecurityConfig).
#
# Trade-off dessa decisão está documentado no ADR.md (seção 6).

ALGORITHM = "HS256"

security = HTTPBearer()


def verify_token(token: str) -> dict | None:
    """Decodifica e valida um JWT usando o segredo compartilhado com o MS Auth."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependência usada em rotas que exigem apenas um usuário autenticado
    (qualquer papel), independente de qual seja o papel (admin ou vendedor).
    """
    payload = verify_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )

    return payload


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Expõe o token JWT "bruto" da requisição atual, para que ele possa ser
    repassado (token relay) em chamadas a outros microsserviços, como o de
    Categorias, preservando o contexto de autenticação do usuário original.
    """
    return credentials.credentials


def require_roles(*allowed_roles: str):
    """Factory de dependência para checagem de RBAC.

    Uso: `Depends(require_roles("admin"))` — exige usuário autenticado E
    com o papel informado, retornando 403 caso contrário.
    """

    def dependency(payload: dict = Depends(get_current_user)) -> dict:
        role = payload.get("role")

        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )

        return payload

    return dependency


# Atalho para o caso mais comum no domínio de Produto: mutações (criar,
# atualizar, desativar) são restritas a administradores, assim como já é
# feito no plus-ms-categorias (POST/PUT/PATCH/DELETE -> hasRole('ADMIN')).
require_admin = require_roles("admin")
