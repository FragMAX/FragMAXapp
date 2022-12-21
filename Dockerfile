FROM ubuntu:18.04

ENV PYTHONUNBUFFERED 1

# for some reason this is needed for 'micromamba activate ...'
ENV MAMBA_EXE="/usr/local/bin/micromamba"
# configure where micromamba stores it's files
ENV MAMBA_ROOT_PREFIX "/opt/mamba"

# add path to adxv command
ENV PATH="/mxn/groups/biomax/wmxsoft/xds_related:${PATH}"

# enable non-interactive mode for apt package utilities while building docker image,
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
        tmux nano less \
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
        # micromamba requires CA certificates when downloading packages
        ca-certificates


COPY deploy/micromamba/micromamba-1.1.0-0.tar.bz2 /tmp
RUN cd /usr/local && tar xvjf /tmp/micromamba-1.1.0-0.tar.bz2  bin/micromamba

# create the FragMAX conda environment
COPY environment.yml /tmp
RUN micromamba shell init --shell=bash
RUN micromamba create -f /tmp/environment.yml
RUN micromamba install -p /opt/mamba/envs/FragMAX -c conda-forge uwsgi=2.0.20

RUN mkdir /app

#
# install FragMAX webapp files
#
WORKDIR /app
COPY fragview fragview/
COPY fragmax fragmax/
COPY projects projects/
COPY jobs jobs/
COPY worker worker/
COPY static static/
COPY conf.py jobsd.py manage.py ./
# docker images are for now hard-coded for 'MAXIV' site
COPY deploy/local_site.py-maxiv local_site.py
# hack to serve css, js etc files from the 'material' package via nginx
RUN ln -s /opt/mamba/envs/FragMAX/lib/python3.10/site-packages/material/static/material static/material
# the django database and site settings file are stored in a volume which is mounted at '/volume' at
RUN ln -s /volume/db .
RUN ln -s /volume/local_conf.py .

# change owernershop of all app files to fragmax-service:MAX-Lab
# use hardcoded UID/GID as we don't have access to symbolic names
# when building the container
RUN chown -R 91121:1300 /app

#
# configure Nginx to serve FragMAX webapp
#
COPY deploy/uwsgi_params .
COPY deploy/fragmax_nginx.conf /etc/nginx/sites-available
RUN ln -s /etc/nginx/sites-available/fragmax_nginx.conf /etc/nginx/sites-enabled/
RUN rm /etc/nginx/sites-enabled/default
# run nginx workers as fragmax-service user
RUN sed -i 's/user .*;/user fragmax-service MAX-Lab;/' /etc/nginx/nginx.conf

# configure supervisord to start all required daemons
COPY deploy/supervisord.conf /etc/supervisor/supervisord.conf

# wrapper for running celery workes processes
COPY deploy/start_celery_workers.sh .

# for SSHing to HPC
COPY --chown=root:1300 deploy/ssh_config /etc/ssh/ssh_config

COPY deploy/start_supervisord.sh .

# include commit description into the image,
# for tracking and trouble shooting
ARG COMMIT_DESC=unknown
RUN echo ${COMMIT_DESC} > commit

CMD [ "/app/start_supervisord.sh" ]
