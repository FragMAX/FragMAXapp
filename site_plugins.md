# Site Plugins

The customization of FragMAX app for deployment to different facilities is achieved via the site-plugins architecture.

## Architecture

A site-plugin is an python package which provides a `SitePlugin` class.
The application will consult an instance of the class, when site specific functionality is required.

The provided `SitePlugin` class must implement all fields and methods defined in `fragview.sites.plugin.SitePlugin` class.
The application will access class's fields and methods to fetch site specific information and invoke site specific behaviour.

Some of the `SitePlugin`'s methods must return objects that implement other classes from the `fragview.sites.plugin` package.

For example the `SitePlugin.get_hpc_runner()` method must return an object that implements all methods of the `fragview.sites.plugin.SitePlugin.HPC` class.
This HPC runner object will be used for running compute heavy jobs, in the site specific way.

For full details of all classes that must be implemented, see the `fragview.sites.plugin` documentation.

## Loading of Site Plugins

The canonical name of the site-plugin that will be used by the application is read from `local_site.SITE` variable.
See the [Site Plugin Configuration](README.md#Site-Plugin-Configuration) on how to configure that variable.

The canonical name is then converted to lower cases and expanded to a full python package name by prepending the "fragview.sites." string.
The full package name then used to instantiate the `SitePlugin` class from that package.

For example, if `SITE` is set to "MAXIV", the application will load the `fragview.sites.maxiv` python package.
From the loaded `fragview.sites.maxiv` package the `SitePlugin` class will be instantiated.

# Available Site Plugins

Currently the FragMAX app have implementation of two site-plugins, for "MAXIV" and "HZB" sites.

## MAX IV Site Plugin

The _MAXIV_ site plugin is used for deployment at MAX IV Laboratory.

### Authentication

The MAXIV plugin uses DUO/ISPyB credentials for authentication.
Authentication with DUO/ISPyB credentials is implemented by `fragview.auth.ISPyBBackend` authentication back-end.
The ISPyBBackend will use ISPyB REST API to check the login credentials.
See the `fragview.auth.ISPyBBackend` module's documentation for details on how to confgure ISPyB authentication.

## HZB Site Plugin

The _HZB_ site plugin is used for deplyment at Helmholtz-Zentrum Berlin facility.

### Authentication

The HZB plugin uses stand-alone FragMAX user accounts, implemented by `fragview.auth.LocalBackend` authentication back-end.
The `LocalBackend` stores user names and password in the application's django database.

To manage the local accounts use the `manage.py` commands.

User can be added with `manage.py add` command:

    ./manage.py adduser <user_name>

The command will prompt for the password.

To change an existing user's password use `manage.py changepassword` command:

    ./manage.py changepassword <user_name>

The command will prompt for the new password.
