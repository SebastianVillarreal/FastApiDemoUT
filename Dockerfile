# Usar una imagen base oficial de Python
FROM python:3.10.13-slim-bullseye

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install unixodbc-dev -y \
    && apt-get install -y gcc default-libmysqlclient-dev pkg-config \
    && apt-get install -y libpq-dev \
    && apt-get install -y curl build-essential \
    && rm -rf /var/lib/apt/lists/*
    

    # Instalar rustup (instala Rust y Cargo)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

    # Configurar el PATH para incluir el binario de cargo
ENV PATH="/root/.cargo/bin:${PATH}"


# DEPENDECES FOR DOWNLOAD ODBC DRIVER
RUN apt-get install apt-transport-https 
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update

# INSTALL ODBC DRIVER
RUN ACCEPT_EULA=Y apt-get install msodbcsql17 --assume-yes

# CONFIGURE ENV FOR /bin/bash TO USE MSODBCSQL17
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile 
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc 



# Establecer el directorio de trabajo en el contenedor
WORKDIR /code

# Copiar los archivos de requisitos e instalar las dependencias
COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade pip \
    && pip install mysqlclient \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt


#RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copiar el resto del código de la aplicación
COPY ./app /code/app

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"]