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
        # for LDAP authentication
        nslcd \
        # for accessing HPC
        ssh \
        # for running the adxv command
        libxt6 \
        # for running multiple processes
        supervisor \
        # for installing and running django webapp
        python3 \
        python3-pip \
        # the web server
        nginx \
    # the nginx <-> django app 'middleware'
    && pip3 install uwsgi==2.0.18

RUN mkdir /app

# install FragMAX webapp dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

#
# install FragMAX webapp files
#
COPY fragview fragview/
COPY fragmax fragmax/
COPY static static/
COPY manage.py deploy/migrate_db.sh ./
RUN ln -s /data/visitors/biomax static/biomax
RUN ln -s /mxn/groups/ispybstorage/pyarch static/pyarch
# hack to serve css, js etc files from the 'material' package via nginx
RUN ln -s /usr/local/lib/python3.6/dist-packages/material/static/material static/material
# the django database is stored in a volume which is mounted at '/volume' at
RUN ln -s /volume/db .

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

# for SSHing to HPC
COPY --chown=root:1300 deploy/ssh_config /etc/ssh/ssh_config

CMD [ "/usr/bin/supervisord", "--nodaemon", "--configuration", "/etc/supervisor/supervisord.conf" ]
