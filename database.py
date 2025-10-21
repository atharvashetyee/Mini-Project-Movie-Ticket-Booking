import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('database.db')
    print("Opened database successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    ''')
    print("Users table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        poster_url TEXT,
        duration_minutes INTEGER
    )
    ''')
    print("Movies table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS shows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER,
        show_date TEXT NOT NULL,
        show_time TEXT NOT NULL,
        FOREIGN KEY(movie_id) REFERENCES movies(id)
    )
    ''')
    print("Shows table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        show_id INTEGER,
        total_price REAL,
        booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(show_id) REFERENCES shows(id)
    )
    ''')
    print("Bookings table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS booked_seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        seat_number TEXT NOT NULL,
        FOREIGN KEY(booking_id) REFERENCES bookings(id)
    )
    ''')
    print("Booked seats table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL
    )
    ''')
    print("Food items table created successfully")

    conn.execute('''
    CREATE TABLE IF NOT EXISTS food_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        item_id INTEGER,
        quantity INTEGER NOT NULL,
        FOREIGN KEY(booking_id) REFERENCES bookings(id),
        FOREIGN KEY(item_id) REFERENCES food_items(id)
    )
    ''')
    print("Food orders table created successfully")

    # Check if admin exists
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE is_admin = 1")
    admin = cursor.fetchone()

    if not admin:
        hashed_password = generate_password_hash('adminpassword', method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                       ('admin', hashed_password, 1))
        print("Admin user created successfully")

    # Add sample food items if they don't exist
    cursor.execute("SELECT COUNT(*) FROM food_items")
    if cursor.fetchone()[0] == 0:
        food_items = [
            ('Popcorn', 150.00),
            ('Nachos', 200.00),
            ('Cola', 80.00),
            ('Veggie Burger', 250.00),
            ('Water Bottle', 40.00)
        ]
        cursor.executemany("INSERT INTO food_items (name, price) VALUES (?, ?)", food_items)
        print("Sample food items added successfully")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
