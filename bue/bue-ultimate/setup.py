"""BUE Ultimate 10/10 - Setup Configuration"""

from setuptools import setup, find_packages

CORE_DEPS = [
    'fastapi>=0.104.0',
    'uvicorn[standard]>=0.24.0',
    'pydantic>=2.4.0',
    'pandas>=2.1.0',
    'numpy>=1.24.0',
    'scipy>=1.11.0',
]

GPU_DEPS = ['cupy-cuda12x>=12.0.0', 'numba>=0.58.0']
FORECASTING_DEPS = ['statsmodels>=0.14.0', 'prophet>=1.1.5', 'tensorflow>=2.15.0']
GRAPHQL_DEPS = ['strawberry-graphql>=0.216.0']
STREAMING_DEPS = ['websockets>=12.0', 'sse-starlette>=1.8.0']

setup(
    name='bue-ultimate',
    version='2.0.0',
    description='BUE Ultimate 10/10 - Category-defining business underwriting platform',
    author='Aetherion',
    packages=find_packages(),
    python_requires='>=3.11',
    install_requires=CORE_DEPS,
    extras_require={
        'gpu': GPU_DEPS,
        'forecasting': FORECASTING_DEPS,
        'graphql': GRAPHQL_DEPS,
        'streaming': STREAMING_DEPS,
        'all': GPU_DEPS + FORECASTING_DEPS + GRAPHQL_DEPS + STREAMING_DEPS,
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.11',
    ],
)
