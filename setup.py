from setuptools import setup, find_packages

setup(
    name='generate-tests',
    version='0.1.0',
    py_modules=['cli'],
    install_requires=[
        'google-generativeai',
        'requests',
        'python-dotenv'
    ],
    entry_points={
        'console_scripts': [
            'generate-tests = cli:main',
        ],
    },
)
