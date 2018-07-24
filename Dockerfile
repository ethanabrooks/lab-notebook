FROM ubuntu:18.04

RUN apt-get update --fix-missing
RUN apt-get install -y tmux git python3.6 python3-pip
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/run_manager
RUN pip3 install tabulate ipdb
COPY setup.py .
COPY README.rst .
COPY runs-git .
COPY runs runs/
RUN pip3 install -e .
#RUN echo 'alias t="python3 -m unittest runs/tests.py"' > /root/.bashrc
CMD ["nosetests", "-x", "-s"]
