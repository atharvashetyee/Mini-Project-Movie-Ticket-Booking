import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import datetime

app = Flask(__name__)
app.secret_key = 'your_very_secret_key'
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = query_db('SELECT * FROM users WHERE id = ?', [session['user_id']], one=True)
    return dict(current_user=user)

@app.route('/')
def index():
    movies = query_db('SELECT * FROM movies')
    return render_template('index.html', movies=movies)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'danger')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    movie = query_db('SELECT * FROM movies WHERE id = ?', [movie_id], one=True)
    today = datetime.date.today().isoformat()
    shows = query_db('SELECT * FROM shows WHERE movie_id = ? AND show_date >= ? ORDER BY show_date, show_time', [movie_id, today])
    return render_template('movie_details.html', movie=movie, shows=shows)

@app.route('/book/<int:show_id>', methods=['GET', 'POST'])
@login_required
def book_show(show_id):
    show = query_db('''
        SELECT s.*, m.title, m.poster_url 
        FROM shows s JOIN movies m ON s.movie_id = m.id 
        WHERE s.id = ?
    ''', [show_id], one=True)

    booked_seats_rows = query_db('''
        SELECT bs.seat_number FROM booked_seats bs
        JOIN bookings b ON bs.booking_id = b.id
        WHERE b.show_id = ?
    ''', [show_id])
    booked_seats = [row['seat_number'] for row in booked_seats_rows]

    food_items = query_db('SELECT * FROM food_items')

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        
        if not selected_seats:
            flash('Please select at least one seat.', 'danger')
            return redirect(url_for('book_show', show_id=show_id))

        seat_price = 180
        total_price = len(selected_seats) * seat_price
        
        db = get_db()
        cursor = db.cursor()
        
        booking_uuid = str(uuid.uuid4().hex)[:10].upper()

        cursor.execute('INSERT INTO bookings (booking_id, user_id, show_id, total_price) VALUES (?, ?, ?, ?)',
                       (booking_uuid, session['user_id'], show_id, total_price))
        booking_db_id = cursor.lastrowid
        
        for seat in selected_seats:
            cursor.execute('INSERT INTO booked_seats (booking_id, seat_number) VALUES (?, ?)', (booking_db_id, seat))

        food_total = 0
        for item in food_items:
            quantity = request.form.get(f"food_{item['id']}")
            if quantity and int(quantity) > 0:
                quantity = int(quantity)
                food_total += item['price'] * quantity
                cursor.execute('INSERT INTO food_orders (booking_id, item_id, quantity) VALUES (?, ?, ?)',
                               (booking_db_id, item['id'], quantity))

        final_total = total_price + food_total
        cursor.execute('UPDATE bookings SET total_price = ? WHERE id = ?', (final_total, booking_db_id))

        db.commit()
        return redirect(url_for('booking_success', booking_id=booking_uuid))

    return render_template('seat_selection.html', show=show, booked_seats=booked_seats, food_items=food_items)


@app.route('/booking_success/<booking_id>')
@login_required
def booking_success(booking_id):
    booking = query_db('''
        SELECT b.booking_id, b.total_price, u.username, s.show_date, s.show_time, m.title
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN shows s ON b.show_id = s.id
        JOIN movies m ON s.movie_id = m.id
        WHERE b.booking_id = ? AND u.id = ?
    ''', [booking_id, session['user_id']], one=True)

    if not booking:
        flash('Booking not found!', 'danger')
        return redirect(url_for('index'))
    
    booking_db = query_db('SELECT id FROM bookings WHERE booking_id = ?', [booking_id], one=True)

    seats = query_db('SELECT seat_number FROM booked_seats WHERE booking_id = ?', [booking_db['id']])
    food_orders = query_db('''
        SELECT fi.name, fo.quantity, fi.price
        FROM food_orders fo
        JOIN food_items fi ON fo.item_id = fi.id
        WHERE fo.booking_id = ?
    ''', [booking_db['id']])

    return render_template('booking_success.html', booking=booking, seats=seats, food_orders=food_orders)

@app.route('/my_bookings')
@login_required
def my_bookings():
    bookings = query_db('''
        SELECT b.booking_id, b.total_price, b.booking_date, s.show_date, s.show_time, m.title
        FROM bookings b
        JOIN shows s ON b.show_id = s.id
        JOIN movies m ON s.movie_id = m.id
        WHERE b.user_id = ?
        ORDER BY b.booking_date DESC
    ''', [session['user_id']])

    bookings_details = []
    for booking in bookings:
        booking_db = query_db('SELECT id FROM bookings WHERE booking_id = ?', [booking['booking_id']], one=True)
        seats = query_db('SELECT seat_number FROM booked_seats WHERE booking_id = ?', [booking_db['id']])
        food_orders = query_db('''
            SELECT fi.name, fo.quantity FROM food_orders fo
            JOIN food_items fi ON fo.item_id = fi.id
            WHERE fo.booking_id = ?
        ''', [booking_db['id']])
        
        bookings_details.append({
            'info': booking,
            'seats': [s['seat_number'] for s in seats],
            'food': food_orders
        })

    return render_template('my_bookings.html', bookings_details=bookings_details)

# --- Admin Routes ---
@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = {
        'total_users': query_db('SELECT COUNT(*) as c FROM users WHERE is_admin = 0', one=True)['c'],
        'total_movies': query_db('SELECT COUNT(*) as c FROM movies', one=True)['c'],
        'total_shows': query_db('SELECT COUNT(*) as c FROM shows', one=True)['c'],
        'total_bookings': query_db('SELECT COUNT(*) as c FROM bookings', one=True)['c']
    }
    return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/movies')
@admin_required
def admin_movies():
    movies = query_db('SELECT * FROM movies')
    return render_template('admin/movies.html', movies=movies)

@app.route('/admin/movies/add', methods=['GET', 'POST'])
@admin_required
def add_movie():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        poster_url = request.form['poster_url']
        duration = request.form['duration']
        
        db = get_db()
        db.execute('INSERT INTO movies (title, description, poster_url, duration_minutes) VALUES (?, ?, ?, ?)',
                   (title, description, poster_url, duration))
        db.commit()
        flash('Movie added successfully!', 'success')
        return redirect(url_for('admin_movies'))
        
    return render_template('admin/add_movie.html')

@app.route('/admin/movies/delete/<int:movie_id>', methods=['POST'])
@admin_required
def delete_movie(movie_id):
    db = get_db()
    
    # It's important to first delete associated data in other tables.
    # Here, we delete all shows scheduled for this movie.
    # To be fully robust, you'd also delete bookings, booked_seats, etc.
    # For simplicity, we'll just delete shows for now.
    db.execute('DELETE FROM shows WHERE movie_id = ?', [movie_id])
    
    # Now, we can safely delete the movie itself.
    db.execute('DELETE FROM movies WHERE id = ?', [movie_id])
    
    db.commit()
    flash('Movie and all its associated shows have been deleted successfully.', 'success')
    return redirect(url_for('admin_movies'))

@app.route('/admin/shows')
@admin_required
def admin_shows():
    shows = query_db('''
        SELECT s.id, s.show_date, s.show_time, m.title 
        FROM shows s JOIN movies m ON s.movie_id = m.id
        ORDER BY s.show_date, s.show_time
    ''')
    return render_template('admin/shows.html', shows=shows)

@app.route('/admin/shows/add', methods=['GET', 'POST'])
@admin_required
def add_show():
    if request.method == 'POST':
        movie_id = request.form['movie_id']
        show_date = request.form['show_date']
        show_time = request.form['show_time']
        
        db = get_db()
        db.execute('INSERT INTO shows (movie_id, show_date, show_time) VALUES (?, ?, ?)',
                   (movie_id, show_date, show_time))
        db.commit()
        flash('Show added successfully!', 'success')
        return redirect(url_for('admin_shows'))
        
    movies = query_db('SELECT id, title FROM movies')
    return render_template('admin/add_show.html', movies=movies)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings_data = query_db('''
        SELECT b.booking_id, u.username, m.title, s.show_date, s.show_time, b.total_price
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN shows s ON b.show_id = s.id
        JOIN movies m ON s.movie_id = m.id
        ORDER BY b.booking_date DESC
    ''')
    
    bookings_details = []
    for booking in bookings_data:
        booking_db = query_db('SELECT id FROM bookings WHERE booking_id = ?', [booking['booking_id']], one=True)
        seats_rows = query_db('SELECT seat_number FROM booked_seats WHERE booking_id = ?', [booking_db['id']])
        seats = [row['seat_number'] for row in seats_rows]
        
        food_orders = query_db('''
            SELECT fi.name, fo.quantity, fi.price 
            FROM food_orders fo
            JOIN food_items fi ON fo.item_id = fi.id
            WHERE fo.booking_id = ?
        ''', [booking_db['id']])
        
        bookings_details.append({
            'info': booking,
            'seats': seats,
            'food_orders': food_orders
        })
        
    return render_template('admin/bookings.html', bookings_details=bookings_details)

if __name__ == '__main__':
    app.run(debug=True)

