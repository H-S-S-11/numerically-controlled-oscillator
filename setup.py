from setuptools import setup, find_packages

setup(
    name="numerically-controlled-oscillator",
    description="nMigen NCO and other signal processing",
    python_requires="~=3.6",
    setup_requires=["wheel", "setuptools", "setuptools_scm"],
    packages=find_packages(exclude=["tests*", "build"]),
)
