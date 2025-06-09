from setuptools import setup, find_packages

setup(
    name="gherkin-headless-generator",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai",
        "python-dotenv",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "generate-tests=cli_tool.cli:main",
            "generate-headlesstest=cli_tool.cli:main_generate_headless_tests"
        ],
    },
)
