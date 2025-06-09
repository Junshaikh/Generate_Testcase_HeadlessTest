from setuptools import setup, find_packages

setup(
    name="testcase-generator",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "google-generativeai",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "generate-tests = cli_tool.cli:main_generate_tests",
            "generate-headlesstest = cli_tool.cli:main_generate_headless_tests",
        ]
    }
)
