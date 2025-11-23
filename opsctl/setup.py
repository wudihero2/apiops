"""
Setup script for opsctl
"""

from setuptools import setup, find_packages
import os


def read_file(filename):
    """Read file contents"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


setup(
    name='opsctl',
    version='0.1.0',
    description='Command line tool for ApiOps',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='ApiOps Team',
    author_email='ops@example.com',
    url='https://github.com/your-org/apiops',
    packages=find_packages(),
    install_requires=[
        'click>=8.0.0',
        'requests>=2.28.0',
        'rich>=13.0.0',
        'pyyaml>=6.0',
    ],
    entry_points={
        'console_scripts': [
            'opsctl=opsctl.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
)
