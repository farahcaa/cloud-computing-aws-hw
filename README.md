# Flask + SQLite3 User Portal on AWS EC2

A Flask app served by Apache (mod_wsgi) on an Ubuntu EC2 instance, with a SQLite3 database.

## Features
- **Register**: username and password (password stored hashed)
- **User details**: first name, last name, email, address
- **Profile page**: shows the stored details after you submit
- **Log in again**: enter your username and password to get your info back
- **File upload**: upload a `.txt` file (e.g. `Limerick.txt`). The file is stored, its word count is shown, and you can download it.

## Files
| File | Purpose |
|------|---------|
| `flaskapp.py` | Flask routes and SQLite logic |
| `flaskapp.wsgi` | mod_wsgi entry point |
| `templates/` | Jinja2 HTML pages (register, login, profile) |
| `static/style.css` | Styling |
| `apache/flaskapp.conf` | Apache virtual host |

## Setup (Ubuntu)
```bash
sudo apt-get update
sudo apt-get install apache2 libapache2-mod-wsgi-py3 python3-pip python3-flask sqlite3
chmod 755 /home/ubuntu/
git clone <this repo> /home/ubuntu/hw-2
sudo cp apache/flaskapp.conf /etc/apache2/sites-available/
sudo a2dissite 000-default && sudo a2ensite flaskapp
# Apache's systemd unit mounts /home read-only; allow writes to the app dir
sudo mkdir -p /etc/systemd/system/apache2.service.d
printf '[Service]\nReadWritePaths=/home/ubuntu/hw-2\n' | sudo tee /etc/systemd/system/apache2.service.d/flaskapp.conf
sudo systemctl daemon-reload && sudo systemctl restart apache2
```

## Database schema
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    filename TEXT,
    wordcount INTEGER
);
```
