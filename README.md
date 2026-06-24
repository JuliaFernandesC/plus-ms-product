# plus-ms-product
 
Microsserviço de domínio **Produto** do sistema Plus — Gestão de Estoque para Loja de Roupas Plus Size.
 
Responsável por: cadastro de produtos, tabelas de medidas, variações de cor/SKU e grade de tamanhos.
 
# Manual de Execução
 
## Configuração
 
### Pré-requisitos
 
| Ferramenta | Versão mínima | Instalação |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| Git | --- | https://git-scm.com/install/ |
 
### Clonagem
 
```bash
git clone <url-deste-repositorio>
cd plus-ms-product
```
 
## Execução
 
Existem duas formas de rodar este serviço: **isolado** (rápido, ideal para desenvolvimento e para testar a API sozinha) ou **integrado** (com Ministack, MS Auth e Shell, simulando o ambiente real).
 
---
 
### Opção A — Isolado (recomendado para desenvolvimento)
 
Usa um banco SQLite local, sem necessidade de Docker nem de outros serviços no ar.
 
1. Criar e ativar o ambiente virtual:
```bash
python -m venv venv
```
 
- Windows:
```powershell
.\venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```
 
2. Instalar as dependências:
```bash
pip install -r requirements.txt
```
> Se o `pip` não for reconhecido, tente `python -m pip install -r requirements.txt`.
 
3. Rodar a API:
```bash
cd src
uvicorn main:app --reload
```
> Se o `uvicorn` não for reconhecido, tente `python -m uvicorn main:app --reload`.
 
4. Acessar:
| Recurso | URL |
|---|---|
| API (raiz) | http://localhost:8000/ |
| Swagger (documentação interativa) | http://localhost:8000/docs |
| Redoc (documentação alternativa) | http://localhost:8000/redoc |
 
> Por padrão o Uvicorn sobe na porta `8000`. Para rodar na porta oficial do serviço (`3002`, igual ao ambiente integrado), use `uvicorn main:app --reload --port 3002`.

> **Autenticação:** todas as rotas (exceto a raiz `/`) exigem um JWT válido no header `Authorization: Bearer <token>`, com o mesmo `JWT_SECRET` usado pelo `plus-ms-auth` (por padrão, `dev-secret`). No modo isolado, sem o MS Auth no ar, gere um token de teste manualmente (ex.: com `python-jose`, usando o mesmo segredo) para testar as rotas pelo Swagger.
 
---
 
### Opção B — Integrado (Ministack + MS Auth + Shell)
 
Sobe o ecossistema completo via Docker Compose, a partir do repositório `plus-infra` (compartilhado entre todos os microsserviços do projeto).
 
1. Clone, no mesmo nível de pasta deste repositório, o `plus-infra`, o `plus-ms-auth`, o `plus-mfe-auth` e o `plus-shell` (veja o README do `plus-ms-auth` para os links).
2. Dentro de `plus-infra`, crie um arquivo `.env` com:
```
DB_HOST=ministack-rds-plus-auth-db
DB_PORT=5432
DB_USER=plus
DB_PASSWORD=plus_secret
DB_NAME=plus_product
JWT_SECRET=dev-secret
MS_AUTH_PORT=3001
MS_PRODUCT_PORT=3002
SHELL_PORT=3000
MFE_AUTH_PORT=4001
```
> `JWT_SECRET` precisa ser **idêntico** ao configurado no `plus-ms-auth` (e no `plus-ms-categorias`), já que os tokens são validados localmente em cada serviço (ver ADR.md).
>
> Opcionalmente, defina `CATEGORIA_SERVICE_URL` (ex.: `http://plus-ms-categorias:3002`) para habilitar a validação cross-service do `categoriaId` ao criar/atualizar produtos. Sem essa variável, a validação é simplesmente pulada (ver ADR.md, seção 6.2).
 
3. Subir os containers:
```bash
docker compose up -d --build
```
 
4. Acessar:
| Serviço | URL local |
|---|---|
| plus-shell | http://localhost:3000 |
| plus-ms-auth | http://localhost:3001 |
| **plus-ms-product** | **http://localhost:3002** |
| **Swagger do plus-ms-product** | **http://localhost:3002/docs** |
| plus-mfe-auth | http://localhost:4001 |
| Ministack | http://localhost:4566 |
 
5. Para parar:
```bash
docker compose down
```
 
## Testes
 
### Testes unitários
Rodam em memória, sem necessidade de Docker.
 
```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```
 
### Testes funcionais
Builda e sobe o container real, e testa via HTTP. Necessita de Docker em execução.
 
```bash
python -m pytest -c pytest-functional.ini
```
 
## CI/CD
 
O pipeline (GitHub Actions, em `.github/workflows/`) roda automaticamente a cada push/PR para a `main`:
- `test.yaml`: executa os testes unitários e funcionais.
- `build.yaml`: builda a imagem Docker e publica no Docker Hub.
## Principais rotas
 
| Método | Rota | Descrição |
|---|---|---|
| POST | `/products` | Cria um produto (com variantes opcionais) |
| GET | `/products` | Lista produtos (paginado) |
| GET | `/products/search` | Busca produtos por filtros (nome, preço, cor, tamanho...) |
| GET | `/products/{id}` | Detalhe do produto, com variantes |
| PUT | `/products/{id}` | Atualiza um produto |
| PATCH | `/products/{id}/disable` | Desativa um produto (soft delete em cascata) |
| POST | `/products/{id}/variants` | Cria uma variante (cor/SKU) para o produto |
| GET | `/products/{id}/variants` | Lista variantes de um produto |
| GET, PUT, PATCH | `/variants/{id}` | Detalhe, atualização e desativação de uma variante |
| POST, GET, PUT, PATCH | `/sizes` | CRUD de tamanhos (grade) |
 
A documentação completa de cada rota (parâmetros, exemplos, respostas) está disponível no Swagger (`/docs`).