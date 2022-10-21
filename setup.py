from setuptools import find_packages, setup

with open('README.md') as readme_file:
    readme = readme_file.read()

def get_requirements(requirements_file='requirements.txt'):
    """Get the contents of a file listing the requirements"""
    lines = open(requirements_file).readlines()
    dependencies = []
    for line in lines:
        dep = line.strip()
        if dep.startswith('git+'):
            # VCS reference for dev purposes, expect a trailing comment
            # with the normal requirement
            __, __, repo = dep.rpartition('=')
            dep = repo + ' @ ' + dep
        if dep:
            dependencies.append(dep)
    return dependencies

setup(
    name='Name Match',
    version='1.2.0',
    description='Tool for probabilistically linking the records of individual entities (e.g. people) within and across datasets',
    author="University of Chicago Crime Lab",
    author_email='mmcneill@uchicago.edu;tlin2@uchicago.edu;zjelveh@umd.edu',
    url='https://github.com/urban-labs/namematch',
    packages=find_packages(),
    include_package_data=True,
    install_requires=get_requirements('requirement/main.txt'),
    package_data={'': ['*.yaml']},
    entry_points={
        'console_scripts': [
            'namematch = namematch.cli:execute']},
    license='University of Chicago Crime Lab',
    keywords='record linkage',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    python_require='>=3.6',
    test_suite='tests',
    tests_require=get_requirements('requirement/dev.txt')
)
