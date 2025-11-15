import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

MONGO_URI = "mongodb+srv://vrebello21_db_user:admin2106@cluster.t7vznud.mongodb.net/"
DATABASE_NAME = "ProjectDatabase"
COLLECTION_NAME = "data"

def connect_db():
    
    try:
        con = MongoClient(MONGO_URI)
        con.admin.command('ping') 
        print("Conectado ao MongoDB com sucesso!")
        db = con.get_database(DATABASE_NAME)
        return db
    except ConnectionFailure as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        return None
    
    
def registerDatabase():
    
    db = connect_db()

    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        drawing_record = {
            # "params": initialParams,
            # "gcode": gcodeResult,
            # "upload_date": datetime.now(),
            "status": "testing",
        }
        result = collection.insert_one(drawing_record)
        print(f"Registro de dado inserido com o ID: {result.inserted_id}")
        return result.inserted_id
    else:
        print("Erro ao inserir dados no banco")
        

if __name__ == "__main__":
    registerDatabase()