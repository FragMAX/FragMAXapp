"""
Django settings for fragmax project.

Generated by 'django-admin startproject' using Django 2.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from typing import Optional
import conf
from fragview.sites import SITE
from conf import REDIS_URL, DATABASE_DIR
# expose these configs below as django settings
from conf import PROJECTS_DB_DIR, PROJECTS_ROOT_DIR, DEPLOYMENT_TYPE  # noqa F401

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xcra)=3kh9#*39o=cj-bdw^rfukhgemgo^hh(k%uvu_@g3dcs#'

DEBUG = conf.DEBUG

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_static_jquery',
    'fragview',
    'material',
    'material.frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'fragview.middleware.login_required',
    'fragview.middleware.no_projects_redirect',
    'fragview.middleware.key_required_redirect',
]

ROOT_URLCONF = 'fragmax.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'fragview.context_processors.site',
                'fragview.context_processors.projects',
                'fragview.context_processors.active_menu',
            ],
        },
    },
]

WSGI_APPLICATION = 'fragmax.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATABASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    SITE.AUTH_BACKEND
]

OPEN_URLS = ["/crypt/"]

# ISPyBBackend authentication settings
ISPYB_AUTH_HOST = "ispyb.maxiv.lu.se"
ISPYB_AUTH_SITE = "MAXIV"

AUTH_USER_MODEL = "fragview.User"

# after login, when no 'next' url is known, goto the 'front' page
LOGIN_REDIRECT_URL = "/"
# when logged out, goto login page
LOGOUT_REDIRECT_URL = "login"

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'CET'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    '/data/visitors/biomax/',
]

#
# Celery (worker threads) config
#
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

#
# HPC (compute cluster) settings
#

# the host we use to manage jobs on HPC
HPC_FRONT_END = "clu0-fe-0"

#
# the URL used to read and write encrypted data, e.g. https://fragmax/crypto/
# must be set in site local settings 'site_settings.py'
#
CRYPT_URL: Optional[str] = None
