# serverledge-solver

## Aggiungere il virtual environment
Dalla linea di comando eseguire:
```
python3 -m venv env
```
Per attivare il virtual environment è necessario eseguire il seguente comando
```
source env/bin/activate
```
Per installare tutti i packages eseguire il seguente comando:
```
pip install -r requirements.txt
```

## Attivare gRPC
Posizionarsi all'interno della cartella src/proto ed eseguire il seguente comando:
```
python3 -m grpc_tools.protoc -I . --python_out=. --pyi_out=. --grpc_python_out=. *.proto
```