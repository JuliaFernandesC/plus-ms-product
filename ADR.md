Trabalho 1 de ES2, Grupo 7

Integrantes: Jasmine Vanzella, Julia Fernandes, Luiza Rosito, Murilo Souza e Rafael Madeira

# Documento de Decisão de Arquitetura — Microsserviço de Produto (Plus Gestão)

## 1. STATUS: Aceito

## 2. CONTEXTO

    O `plus-ms-product` é o microsserviço de domínio responsável pelo cadastro de
    produtos, grade de tamanhos e variações de cor/SKU do sistema Plus — gestão de
    estoque para vestuário plus size. Ele segue a mesma arquitetura distribuída
    (Microsserviços + Microfrontends) descrita no ADR do `plus-ms-auth`, e este
    documento complementa aquele, registrando as decisões específicas do domínio de
    Produto: integração com autenticação/RBAC, relacionamento com os MS de
    Categoria e Fornecedor, e tratamento de erros de integridade de dados.

## 3. DECISÃO ARQUITETURAL

    Mantém-se o estilo de Arquitetura em Camadas (Controllers, Services implícitos
    nos próprios controllers para esse domínio mais simples, Models/DTOs), com
    persistência via SQLAlchemy e exposição via FastAPI — consistente com o padrão
    já adotado no `plus-ms-auth`.

    ### 3.1. Autenticação e Autorização (JWT/RBAC)

    O MS de Produto **não emite tokens** — essa responsabilidade é exclusiva do
    `plus-ms-auth`. Para validar os tokens recebidos, o MS de Produto **replica
    localmente** a lógica de verificação de JWT (`app/config/security.py`):
    decodifica o token com o mesmo algoritmo (HS256) e o mesmo segredo
    compartilhado (`JWT_SECRET`) configurados no `plus-ms-auth`.

    Essa é a mesma estratégia já adotada pelo `plus-ms-categorias` (implementado em
    Java/Spring, com seu próprio `HmacSha256JwtDecoder`): cada microsserviço de
    recurso valida o JWT de forma **stateless**, sem precisar fazer uma chamada de
    rede ao MS de Auth a cada requisição.

    RBAC: leitura (`GET`) é permitida a qualquer usuário autenticado
    (`admin` ou `vendedor`); mutações (`POST`, `PUT`, `PATCH`) em produtos,
    variantes e tamanhos são restritas ao papel `admin` — espelhando exatamente a
    regra já aplicada no `plus-ms-categorias`
    (`hasRole('ADMIN')` para `POST`/`PUT`/`PATCH`/`DELETE`).

    ### 3.2. Relacionamento com Categoria

    Um Produto referencia **uma única** categoria (`categoriaId`), não uma lista.
    Essa decisão decorre diretamente do modelo de domínio do `plus-ms-categorias`:
    lá, `Categoria` é uma estrutura em **árvore** (`categoriaPaiId` aponta para uma
    única categoria-pai). Permitir que um produto referencie múltiplas categorias
    quebraria essa hierarquia (a noção de "categoria mais específica" deixaria de
    existir) e duplicaria, no MS de Produto, uma responsabilidade de modelagem que
    já pertence ao MS de Categorias. Se for necessário, no futuro, listar produtos
    por uma categoria "ampla" (ex.: "Vestidos" abrangendo "Vestidos Longos" e
    "Vestidos Curtos"), isso deve ser resolvido percorrendo a árvore de categorias
    no `plus-ms-categorias` (via `categoriaPaiId`), e não com uma relação N:N no
    Produto.

    A validação cross-service do `categoriaId` é feita de forma síncrona, via HTTP
    (`app/clients/categoria_client.py`), no momento da criação/atualização do
    produto, repassando o JWT do usuário autenticado (token relay) para a chamada
    `GET /categorias/{id}` do `plus-ms-categorias` — já que essa rota também exige
    autenticação. Essa validação é **fail-open**: se o serviço de Categorias não
    estiver configurado ou não responder a tempo, o produto é criado/atualizado
    normalmente (ver trade-offs, seção 6.2). A validação só **bloqueia** a operação
    quando o serviço de Categorias confirma (HTTP 404) que a categoria não existe.

    ### 3.3. Relacionamento com Fornecedor

    O `fornecedorId` é armazenado, mas **não é validado** cross-service nesta
    entrega: não há, até o momento, um microsserviço de Fornecedor disponível no
    ecossistema Plus. Essa é uma limitação conhecida e documentada (seção 6.2),
    não um descuido — assim que o MS de Fornecedor existir, a mesma estratégia
    usada para `categoriaId` (cliente HTTP com fail-open) pode ser replicada.

    ### 3.4. Consistência na criação de variantes aninhadas

    A criação de um produto já com variantes (`POST /products` com o campo
    `variantes`) aplica exatamente as mesmas validações da rota dedicada
    (`POST /products/{id}/variants`): o `tamanhoId` de cada variante precisa
    existir, e o `sku` não pode colidir com nenhuma variante já cadastrada — nem
    com outra variante dentro do mesmo payload. Isso evita que a criação aninhada
    seja uma forma de contornar as regras de negócio aplicadas na rota dedicada.

    ### 3.5. Tratamento de erros de integridade

    Toda escrita no banco (`db.commit()`) é protegida contra `IntegrityError`
    (ex.: SKU duplicado por uma corrida entre requisições concorrentes, que passe
    pelas validações manuais mas colida no commit). Os pontos de escrita mais
    sensíveis tratam o erro localmente, convertendo para `409 Conflict` com uma
    mensagem amigável. Como rede de segurança adicional, `main.py` registra um
    `exception_handler` global para `IntegrityError`, garantindo que nenhum erro
    desse tipo escape como um `500` genérico, mesmo que apareça em um ponto do
    código ainda não coberto por um tratamento específico.

## 4. FLUXO GERAL

    O Shell/MFE envia o JWT obtido do `plus-ms-auth` (`POST /auth/login`) no header
    `Authorization: Bearer <token>` de toda requisição ao MS de Produto. O MS de
    Produto valida a assinatura/expiração do token localmente
    (`app/config/security.py`) e checa o papel (`role`) da claim do JWT para
    decidir se a operação é permitida (RBAC). Ao criar/atualizar um produto com
    `categoriaId`, o MS de Produto repassa esse mesmo token em uma chamada
    `GET /categorias/{id}` ao `plus-ms-categorias`, para confirmar que a categoria
    existe antes de persistir a referência.

## 5. TECNOLOGIAS ADOTADAS

    - Python 3.12 + FastAPI
    - SQLAlchemy (PostgreSQL em produção; SQLite em desenvolvimento isolado/testes)
    - python-jose (decodificação de JWT, mesma biblioteca usada no `plus-ms-auth`)
    - httpx (cliente HTTP para a validação cross-service de `categoriaId`)
    - Docker
    - Pytest (testes unitários em memória + testes funcionais contra o container real)

## 6. TRADE-OFFS

### 6.1. VANTAGENS

    - Validação de JWT stateless: nenhuma chamada de rede ao MS de Auth é
      necessária para autenticar uma requisição, reduzindo latência e evitando que
      uma indisponibilidade do MS de Auth derrube os demais serviços que já têm
      usuários com tokens válidos em mãos.

    - RBAC consistente entre serviços: a mesma regra (`admin` escreve, qualquer
      autenticado lê) é aplicada da mesma forma no MS de Produto e no MS de
      Categorias, facilitando o raciocínio sobre permissões em todo o sistema.

    - Acoplamento fraco e deliberado com Categoria/Fornecedor: o MS de Produto não
      mantém uma foreign key física para outros bancos de dados, preservando a
      independência de deploy/escala de cada serviço.

### 6.2. DESVANTAGENS/RISCOS

    - Duplicação de segredo e lógica de verificação de JWT: o `JWT_SECRET` e o
      código de decodificação/validação existem tanto no `plus-ms-auth` quanto no
      `plus-ms-product` (e, em Java, no `plus-ms-categorias`). Isso é uma escolha
      consciente (evita uma chamada de rede por requisição autenticada), mas exige
      governança: se o segredo rotar, **todos** os serviços precisam ser
      atualizados juntos, e qualquer mudança na lógica de validação (ex.: novos
      claims, novo algoritmo) precisa ser replicada manualmente em cada serviço.

    - Validação cross-service fail-open: se o `plus-ms-categorias` estiver fora do
      ar, é possível criar um produto com um `categoriaId` que mais tarde se
      revele inválido. Optamos por isso para não acoplar a disponibilidade do MS
      de Produto à do MS de Categorias, mas isso significa que a consistência
      entre os dois é **eventual**, não imediata — pode haver, temporariamente,
      produtos com referências "pendentes de confirmação".

    - Nenhuma validação para `fornecedorId`: como não existe um MS de Fornecedor
      no ecossistema atual, qualquer valor é aceito para esse campo. Isso é uma
      lacuna conhecida, não uma decisão definitiva.

    - Sem mecanismo de invalidação/expiração centralizada: como em qualquer
      esquema de JWT stateless puro, um token comprometido continua válido até
      expirar — não há, hoje, uma blacklist compartilhada entre os serviços.
