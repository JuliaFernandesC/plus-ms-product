"""
Dados mockados de Categoria e Fornecedor, no mesmo formato (mesmos campos,
mesmo tipo de ID) que os respectivos microsserviços reais retornariam.

Os IDs aqui devem ser os mesmos usados no mock do plus-mfe-product,
senão o formulário de cadastro vai sempre falhar a validação.
"""

# Categoria: id é INTEIRO no MS real (plus-ms-categorias).
MOCKED_CATEGORIAS = [
    {"id": 1, "nome": "Calças"},
    {"id": 2, "nome": "Vestidos"},
    {"id": 3, "nome": "Blusas"},
    {"id": 4, "nome": "Saias"},
    {"id": 5, "nome": "Jaquetas"},
]

# Fornecedor: id é STRING/UUID no MS real (chave-ms-supplier).
MOCKED_FORNECEDORES = [
    {"id": "f1e2d3c4-b5a6-7890-abcd-ef1234567890", "nome": "PlusWear Confecções"},
    {"id": "a9b8c7d6-e5f4-3210-fedc-ba0987654321", "nome": "Bella Moda Plus"},
    {"id": "11112222-3333-4444-5555-666677778888", "nome": "Atelier Grandeza"},
]


def mocked_categoria_exists(categoria_id) -> bool:
    ids_validos = {str(c["id"]) for c in MOCKED_CATEGORIAS}
    return str(categoria_id) in ids_validos


def mocked_fornecedor_exists(fornecedor_id) -> bool:
    ids_validos = {c["id"] for c in MOCKED_FORNECEDORES}
    return fornecedor_id in ids_validos