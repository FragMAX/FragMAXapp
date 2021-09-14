# Operating FragMAXapp

This document contains information useful for operators of FragMAXapp.
The operators is someone who is tasked with running and administrating the application at some specific deployment site.

## Fragment Libraries

FragMAXapp supports defining fragment libraries.
A fragment library is a collection of small molecules, so called fragments.
Each fragment have a library unique fragment code and it's associated SMILES definition.
The fragment code allows to denote the fragment in non-ambiguous way.
SMILES define the fragment's chemical structure.

The FragMAXapp supports providing multiple fragment libraries.
The available libraries for the user project are listed under the `Libraries` section of the app.
When a new project is created, the fragment used for each crystal,
are denoted by specifying the library name and the fragment code.

### Managing Fragment Libraries

New fragment library can be added with `manage.py addlib` command:

    ./manage.py addlib <library_file>

The `<library_file>` is a yaml file that specifies library's name and lists all the fragments.
Below is an example library file:

    name: ExampleLib
    fragments:
      EX01: O=C1N[C@@H](CO1)C1=CC=CC=C1
      EX02: CN1CCCCS1(=O)=O
      EX03: CC1=CC=C(S1)C1=CC(=NN1)C(O)=O

The above file specifies fragment library named `ExampleLib`.
The specified library contains fragments with codes `EX01`, `EX02`, `EX03`.

Note that currently there is no straight-forward way to edit or delete an existing library.
For this kind of operation, you'll need to manipulate the FragMAXapp django database.
