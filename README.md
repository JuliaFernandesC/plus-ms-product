# plus-ms-product

## rodando so o ms-product:
cd plus-ms-product

python -m venv venv

# Windows:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

cd src

uvicorn main:app --reload

- Swagger:
http://localhost:8000/docs