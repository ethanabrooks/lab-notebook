# A Dockerfile that sets up a full Gym install
FROM ubuntu:16.04

RUN apt-get update --fix-missing
RUN apt-get install -y tmux git python3 python3-pip
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/run_manager
COPY runs/ .
COPY setup.py .
COPY README.rst .
RUN pip3 install -e .

WORKDIR /root
CMD ["python3", "-m", "unittest", "runs/tests.py"]
