FROM ubuntu:18.04
ENV PYTHONUNBUFFERED 1

# add path to adxv command
ENV PATH="/mxn/groups/biomax/wmxsoft/xds_related:${PATH}"

# enable non-interactive mode for apt package utilities while build docker image,
# so that we don't get any interactive questins when installing packages
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    # prepare for noninteractive nslcd package installation
    && apt-get -y install debconf-utils \
    && echo "nslcd	nslcd/ldap-uris	string dummy" | debconf-set-selections \
    && echo "nslcd	nslcd/ldap-base	string dummy" | debconf-set-selections \
    && echo "libnss-ldapd	libnss-ldapd/nsswitch	multiselect	passwd, group, shadow" | debconf-set-selections \
    && apt-get -y  install \
        # for troubleshooting
        nano \
        # for LDAP authentication
        nslcd \
        # for accessing HPC
        ssh \
        # for running the adxv command
        libxt6 \
        # for running multiple processes
        supervisor \
        # for django <-> celery communication
        redis-server \
        # the web server
        nginx \
        # adxv dependency
        libgomp1 \
        # used to add 'conda' deb repository
        wget \
        gpg

#
# add 'conda' deb repository
#
RUN wget --quiet  --output-document=- https://repo.anaconda.com/pkgs/misc/gpgkeys/anaconda.asc | \
        gpg --dearmor > conda.gpg \
    && install -o root -g root -m 644 conda.gpg /usr/share/keyrings/conda-archive-keyring.gpg
COPY deploy/conda.list /etc/apt/sources.list.d/

# install 'conda' command
RUN apt-get update \
    && apt-get install conda

# create the FragMAX conda environment
COPY environment.yml /tmp
RUN . /opt/conda/etc/profile.d/conda.sh \
    && conda env create -f /tmp/environment.yml \
    && conda activate FragMAX \
    && conda install -c conda-forge uwsgi=2.0.18

RUN mkdir /app

#
# install FragMAX webapp files
#
WORKDIR /app
COPY fragview fragview/
COPY fragmax fragmax/
COPY worker worker/
COPY static static/
COPY manage.py deploy/migrate_db.sh ./
# hack to serve css, js etc files from the 'material' package via nginx
RUN ln -s /opt/conda/envs/FragMAX/lib/python3.6/site-packages/material/static/material static/material
# the django database and site settings file are stored in a volume which is mounted at '/volume' at
RUN ln -s /volume/db .
RUN ln -s /volume/site_settings.py .

# change owernershop of all app files to biomax-service:MAX-Lab
# use hardcoded UID/GID as we don't have access to symbolic names
# when building the container
RUN chown -R 1990:1300 /app

#
# configure Nginx to serve FragMAX webapp
#
COPY deploy/uwsgi_params .
COPY deploy/fragmax_nginx.conf /etc/nginx/sites-available
RUN ln -s /etc/nginx/sites-available/fragmax_nginx.conf /etc/nginx/sites-enabled/
RUN rm /etc/nginx/sites-enabled/default
# run nginx workers as biomax-service user
RUN sed -i 's/user .*;/user biomax-service MAX-Lab;/' /etc/nginx/nginx.conf

# configure supervisord to start all required deamons
COPY deploy/supervisord.conf /etc/supervisor/supervisord.conf

# wrapper for running celery workes processes
COPY deploy/start_celery_workers.sh .

# for SSHing to HPC
COPY --chown=root:1300 deploy/ssh_config /etc/ssh/ssh_config

COPY deploy/start_supervisord.sh .
CMD [ "/app/start_supervisord.sh" ]
