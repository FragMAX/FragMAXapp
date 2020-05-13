#!/usr/bin/env python

import os
import sys
from os import path
import requests
import argparse


def _err_exit(err_msg):
    print(err_msg)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="handle fragmax encrypted files")
    parser.add_argument("url")
    parser.add_argument("auth_tok")
    parser.add_argument("command", choices=["fetch", "upload", "upload_dir"])
    parser.add_argument("src_file")
    parser.add_argument("dest_file")

    return parser.parse_args()


def _get_file(url, auth, src_file):
    print(f"get {src_file}")

    r = requests.post(url,
                      data=dict(auth=auth,
                                operation="read",
                                filepath=src_file))
    if r.status_code != 200:
        _err_exit(f"error fetching {src_file}: {r.text}")

    return r.content


def _upload_file(url, auth, src_file, dest_file):
    print(f"upload {src_file} -> {dest_file}")

    with open(src_file, "rb") as f:
        r = requests.post(url,
                          data=dict(auth=auth,
                                    operation="write",
                                    filepath=dest_file),
                          files=dict(file=f))

    if r.status_code != 200:
        _err_exit(f"error uploading {src_file}: {r.text}")


def _do_fetch(args):
    file_data = _get_file(args.url, args.auth_tok, args.src_file)

    with open(args.dest_file, "bw") as f:
        f.write(file_data)


def _do_upload(args):
    _upload_file(args.url, args.auth_tok, args.src_file, args.dest_file)


def _dir_tree(top):
    for dir, _, files in os.walk(top):
        for file in files:
            yield path.join(dir, file)


def _do_upload_dir(args):
    top_dir = args.src_file
    dest_dir = args.dest_file

    for full_path in _dir_tree(top_dir):
        relative_path = full_path[len(top_dir)+1:]
        dest_path = path.join(dest_dir, relative_path)
        _upload_file(args.url, args.auth_tok, full_path, dest_path)


def main():
    args = parse_args()

    if args.command == "fetch":
        _do_fetch(args)
    elif args.command == "upload":
        _do_upload(args)
    elif args.command == "upload_dir":
        _do_upload_dir(args)


main()
