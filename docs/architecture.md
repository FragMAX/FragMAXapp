# Application Components

The FragMAX webapp consists of these major components:

 * Web Application
 * Workers Threads
 * Jobs Manager
 * Redis Server

## Web Application

The _Web Application_ component implements the web based UI of the FragMAX.

It is build using Django framework, and implements the [wsgi](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) interface.

## Worker Threads

The _Worker Threads_ component handles performing long-running tasks, not suitable to be performed on web-request threads.

The workers are implemented using [celery](https://docs.celeryproject.org/) framework.
Workers are configured to receive tasks from the _Web Application_ component via Redis server.

Note that the heavy data processing is managed by the _Jobs Manager_ component, see below.

## Jobs Manager

The Jobs Manager daemon, `jobsd`, manages running the heavy data processing jobs.
These jobs are mainly used for analysing the crystallographic data, using third party software packages.
The jobs are normally run on an HPC cluster.
The `jobsd` submits the jobs to the HPC scheduling software and monitors job's status.
The `jobsd` also supports running jobs locally, which is used for book-keeping tasks, i.e. updating results tables.

The jobs are submitted and monitored by _Web Application_ using a host local Unix socket.
A custom IPC protocol is used on that socket.

### HPC Flavors

The Jobs Manager daemon supports using different HPC scheduling software, using different `runner` implementations.
The `runner` used at specific site is configured by the `site-plugin`,
see [site plugins](docs/site_plugins.md) for more information in site-plugins.

Currently, two flavors of HPC schedulers are supported, `slurm` and `local`.
The `slurm` runner schedules jobs using [SLURM](https://slurm.schedmd.com/) workload manager.
The `local` runner runs jobs on the local host, by starting new process for each scheduled job.

## Redis Server

The _Redis Server_ is used for communication between the application components.

It is used for submitting tasks to the _Workers Threads_, using the celery protocol.

It is also used for synchronization between processes, using distributed locks.
The FragMAXapp uses a [red lock](https://redis.io/topics/distlock) to implement locks that work across processes.