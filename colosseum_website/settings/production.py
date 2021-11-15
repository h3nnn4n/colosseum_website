import django_heroku

from .base import *


ENVIROMENT = "production"

DEBUG = False

django_heroku.settings(locals())
