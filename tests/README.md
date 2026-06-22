Como rodar testes unitrios:
cd plus-ms-product
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest

Rodar testes funcionais:

Docker instalado e ativo
cd plus-ms-product
pip install -r requirements.txt -r requirements-dev.txt (se ainda não instalou)
python -m pytest -c pytest-functional.ini