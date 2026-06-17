from setuptools import setup, find_packages

setup(
    name="fusion-judge",
    version="0.1.0",
    description="OpenRouter Fusion-style multi-model synthesis — 3 panelists + judge via DeepSeek API",
    author="EVOLVE Agent",
    py_modules=["judge"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            "fusion-judge=judge:main",
        ],
    },
    python_requires=">=3.8",
)
