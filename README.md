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
Lato Server: posizionarsi all'interno della cartella src/proto ed eseguire il seguente comando:
```
python3 -m grpc_tools.protoc -I . --python_out=. --pyi_out=. --grpc_python_out=. *.proto
```

Lato Client: posizionarsi all'interno della cartella client/src/proto ed eseguire il seguente comando:
```
protoc --proto_path proto --go_out proto --go-grpc_out proto proto/*.proto
```

## Go modules
Per poter inizializzare i go modules e testare il lato client (seguire in caso le istruzioni a linea di comando):
```
go mod init client
go mod tidy
go build
```

## Build dell'immagine Docker
Per poter fare la build dell'immagine di docker, assegnandole un nome e un indirizzo dove ascoltare per eventuali richieste, eseguire il seguente comando:
```
docker run --publish 2500:2500 --name Solver serverledge-solver
```

