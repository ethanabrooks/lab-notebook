# A Dockerfile that sets up a full Gym install
FROM ubuntu:16.04

RUN apt-get update --fix-missing
RUN apt-get install -y tmux git python3 python3-pip
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
RUN git config --global user.email "you@example.com"
RUN git config --global user.name "Your Name"

WORKDIR /usr/local/run_manager
COPY setup.py .
COPY runs-git .
COPY README.rst .
COPY runs runs/
RUN pip3 install -e .
#RUN echo 'alias t="python3 -m unittest runs/tests.py"' > /root/.bashrc
CMD ["nosetests -x"]
