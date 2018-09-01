import setuptools

with open('README.MD', 'r') as File:
    long_description = File.read() 

setuptools.setup(
    name='download_queue',
    version='1.1.0',
    author='Mohkale',
    auther_email='Mohkalsin@gmail.com',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/MoHKale/DownloadQueue',
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
