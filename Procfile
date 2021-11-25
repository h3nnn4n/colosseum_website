release: python manage.py migrate
web: gunicorn colosseum_website.wsgi --workers=2 --preload --log-file=-
