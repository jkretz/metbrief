
## Installation (tested on macOS and Windows)

1. Install LibreOffice for your [respective system](https://de.libreoffice.org/download/download/)

2. Install Miniconda or Anaconda (if not already done). Follow the [respective instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html#regular-installation) for your operating system.

3. Open a Terminal / Anaconda Prompt (under Windows)

4. If not already installed, a version of git is needed to clone repository of the checker from GitHub. It can be installed using conda:
    ```bash
   conda install -c anaconda git
    ```
5. Clone this repository:

   ```bash
   git clone https://github.com/jkretz/metbrief.git
   cd atmodat_data_checker
   ```

6. Create the conda environment and install the needed anaconda packages:
   ```bash
   conda env create -f environment.yml
   conda activate metbrief
   ```
   
## Run


   
