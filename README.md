Movie Ticket Booking System

**A full-stack web application for booking movie tickets, built with Python, Flask, and SQLite3. Features a user booking interface and a full admin panel for site management.
**-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Key Features

User Authentication: Secure registration and login.

Interactive Seat Selection: Dynamic seat map with real-time price calculation.

Admin Panel: Manage movies, schedule shows, and view all bookings.

**CRUD Functionality: Admins can create, read, update, and delete movies.
**-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Tech Stack

**Backend: Python, Flask | Frontend: HTML, Tailwind CSS, JavaScript | Database: SQLite3
**-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Quick Start

1. Setup Environment:

Clone the repo, create a virtual environment, and activate it.
git clone [https://github.com/your-username/movie-ticket-system.git](https://github.com/your-username/movie-ticket-system.git)
cd movie-ticket-system
python -m venv venv && source venv/bin/activate # Or venv\Scripts\activate for Windows


2. Install Dependencies:

Create a requirements.txt file with "Flask" and "Werkzeug" then run:
pip install -r requirements.txt


3. Initialize Database:
(Run this once to create the database.db file and the admin user.)

python database.py


4. Run the App:

flask run

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
The application is now live at http://127.0.0.1:5000.

Admin Login:

Username: admin

Password: adminpassword


User Login: Register a new account on the site.


