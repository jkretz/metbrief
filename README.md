
## Installation (tested on macOS and Windows)

1. Install LibreOffice for your [respective system](https://de.libreoffice.org/download/download/)

2. Install Miniconda or Anaconda (if not already done). Follow the [respective instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html#regular-installation) for your operating system.

3. Download a zipped version of the repository (Click on Code and you will find a button to download it) and unzip it. 

4. Alternatively, it also can be downloaded via git.
    ```bash
   git clone https://github.com/jkretz/metbrief.git
    ```
5. Open a Terminal / Anaconda Prompt (under Windows) and navigate to the (unziped) directory of the repository.

6. Create the conda environment and install the needed anaconda packages:
   ```bash
   conda env create -f environment.yml
   conda activate metbrief
   ```
   
7. Enter your flugwetter.de and TopMeteo user detail in `user_details.py`.
   
## Run


   
