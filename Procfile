release: python manage.py migrate
web: gunicorn colosseum_website.wsgi --preload --log-file=-
