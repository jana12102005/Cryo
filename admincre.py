from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Your actual MongoDB connection string
MONGO_URI = "mongodb+srv://cryoemiisc:GZWpObsk1L7vIydQ@allregesterdata.eygquiu.mongodb.net/cryo_em_db?retryWrites=true&w=majority&appName=ALLREGESTERDATA"

try:
    # Establish connection
    client = MongoClient(MONGO_URI)
    db = client.cryo_em_db
    users_collection = db.users

    # Check if the admin user already exists
    if users_collection.count_documents({'username': 'admin'}) == 0:
        # Hash the default password
        hashed_password = generate_password_hash('admin123')
        
        # Insert the new admin user document
        users_collection.insert_one({
            'username': 'admin',
            'password': hashed_password
        })
        print("✅ Admin user created successfully!")
    else:
        print("ℹ️ Admin user already exists.")

except Exception as e:
    print(f"❌ An error occurred: {e}")