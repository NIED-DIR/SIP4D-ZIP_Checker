# -*- coding: utf-8 -*-
""" setup script. """

import subprocess
from setuptools import setup, find_packages

setup(
    name="Sip4dzipChecker",
    author="NIED-DIR",
    author_email="sip4d_info@bosai.go.jp",
    url="https://github.com/NIED-DIR/SIP4D-ZIP_Checker",
    version="1.2.0",
    description="SIP4D-ZIP Checker",
    license="MIT",
    packages=find_packages(),
    package_data={"Sip4dzipChecker": ["template/**/*"]},
    install_requires=[
        "setuptools",
        "zipfile36; python_version<'3.8'",
    ],
)