FROM continuumio/miniconda3

ENV PATH="/root/miniconda3/bin:${PATH}"

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN apt-get update && apt-get install -y glpk-utils

RUN conda create -n twinp2g-env python=3.11.3 -y && \
    echo "conda activate twinp2g-env" >> ~/.bashrc && \
    conda init bash

RUN /bin/bash -c "source activate twinp2g-env && \
    pip3 install --no-cache-dir -r requirements.txt"

COPY . .

EXPOSE 8501

SHELL ["conda", "run", "-n", "twinp2g-env", "/bin/bash", "-c"]

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "twinp2g-env", "streamlit", "run", "inputs.py", "--server.port=8501", "--server.address=0.0.0.0"]
