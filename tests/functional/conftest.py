"""
Configuração compartilhada dos testes FUNCIONAIS do MS de Produto.

Diferente dos testes unitários (que chamam o app em memória), aqui o
fluxo é: builda a imagem Docker do serviço -> sobe um container de
verdade -> espera ele responder -> roda os testes batendo HTTP real
nele -> derruba o container no final.

Isso espelha exatamente o padrão usado no exemplo do professor
(test/functional/setup.js e teardown.js), só que em Python/pytest.

Pré-requisito para rodar: ter o Docker instalado e rodando na máquina
(ou no runner do GitHub Actions, que já vem com Docker por padrão).
"""
import subprocess
import time

import pytest
import requests

CONTAINER_NAME = "plus-ms-product-func-test"
IMAGE_NAME = "plus-ms-product-func-test"
HOST_PORT = 3102
CONTAINER_PORT = 3002
BASE_URL = f"http://localhost:{HOST_PORT}"


def _wait_for_app(url: str, retries: int = 40, delay_seconds: float = 0.5) -> None:
    for _ in range(retries):
        try:
            response = requests.get(url, timeout=2)
            if response.ok:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(delay_seconds)
    raise RuntimeError(f"Aplicação em {url} não respondeu a tempo")


@pytest.fixture(scope="session", autouse=True)
def product_service_container():
    # Remove qualquer container antigo de execuções anteriores que tenham travado
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

    subprocess.run(["docker", "build", "-t", IMAGE_NAME, "."], check=True)

    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{HOST_PORT}:{CONTAINER_PORT}",
            IMAGE_NAME,
        ],
        check=True,
    )

    try:
        _wait_for_app(f"{BASE_URL}/")
        yield BASE_URL
    finally:
        subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)
        subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)
