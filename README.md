# Q-voter model generator

![GitHub last commit](https://img.shields.io/github/last-commit/o-Mateo-o/q-voter-generator)

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
[![Licence](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=for-the-badge)](./LICENSE)

## Table of contents

<!-- TODO: add -->

## Description

This app serves as a handy tool to create **exit time** and **exit probability** plots for **$q$-voter model**[^1] on different parameter sets, including networks. It comes with predefined set of graphs and automatically managed, efficient simulating system.

Just specify the required plots in a JSON file, open the app and forget about the other tedious steps!

On output you will get the folder with *.pdf* plot files and the *.tex* embeding them along with the descriptions (currently in Polish , but configuration is possible).

[^1]: Details introduced in C. Castellano, M.A. Munoz, R. Pastor-Satorras, [*The non-linear q-voter model*](https://arxiv.org/abs/0907.1775)

### Structure

Main project folder contains the Python requirements (`requirements.txt`), batch scripts described in [usage](#usage) section (`auto-q-voter.bat`, `q-voter.bat`), and the `qvoterapp` application directory. Except for that it will be place for `data.xml` base (**do not modify it!**), input specification files - as `plot.spec.json`, and virtual environment files.

When it comes to `qvoterapp`, it can be divided into Julia module(`jlhelpers`), Python module (`pyhelpers`), standalone Python script (`qvoter.py`) and Julia package provider (`packages.jl`). The external scripts will utilize all of them, so for basic usage you don't have to worry about this part.

## Usage

### Quick guide

1. Make sure you have installed both **Python** and **Julia** on your device. Stable versions for the app are specied in [technologies](#technologies) section.
2. Go to the project folder (`q-voter-generator`) and open `q-voter.bat` script. If using **CMD**, type

   ```batch
   chdir your\path\to\q-voter-generator
   q-voter.bat
   ```

   If you are using the app for the first time, exectuion might take longer, for it automatically sets up environments and installs packages for both Python and then Julia.

### Help

There are some additional script options. You can always see quick help calling

   ```batch
   chdir your\path\to\q-voter-generator
   q-voter.bat -h
   ```

### *One-clicker* execution

For the most basic *define plots & simulate & plot* workflow you can use automated script `auto-q-voter.bat`. It will open notebook to allow you define the plot specifications. After you finish and close the file, the main script would be called.

You can simply copy it to the desktop or anywhere you want and run by double-clicking. However, before usage **remember to change the project folder path in its second line!**

## JSON specification file

### Rules

### Example

```python
{   
    # FIRST PLOT
    "first.sample.plot": {
        # values related to the plot
        "plot.args": "model.x", 
        "plot.vals": "exit_proba",
        "plot.group": "model.q", # for only one group do not add this row
        # additionally `plot.valscaling` can be added
        # values related to the network
        "net.net_type": "BA",
        "net.size": 200,  # * single number value type
        "net.k": 1,  # * single number value type
        # method related value
        "method.mc_runs": 1000, # without this line, 1000 is taken on default
        # values describing the model
        "model.x": {
            # * range value type
            "start": 0,
            "step": 0.1,
            "stop": 1
        },
        "model.q": [
            # * list value type
            1,
            2,
            3
        ],
        "model.eps": 0.1
    },
    # SECOND PLOT
    "second.sample.plot": {
        "plot.args": "net.size",
        "plot.vals": "exit_time",
        "plot.group": "model.eps",
        "net.net_type": "C",
        "model.x": 0.5,
        "model.q": 4,
        # no eps & size specified before!
        "groups": [
            # it's possible to get separate sizes for each eps
            {
                "model.eps": 0.1,
                "net.size": [
                    10,
                    20,
                    50,
                    70,
                    100,
                    200,
                    500,
                    1000,
                    5000,
                    1000
                ]
            },
            {
                "model.eps": 0.23,
                "net.size": [
                    10,
                    20,
                    50,
                    70,
                    100,
                    200,
                    500,
                    1000
                ]
            }
        ]
    }
}
```

## Models

Only the models predefined in [`qvoterapp/jlhelpers/models.jl`](qvoterapp/jlhelpers/models.jl) can be used. In the last definition, there is a dictionary of models' *key names*. Users should also stick to this convention of naming when creating new models.

Existing network models along with their parameters are:

### Barabasi-Albert (*key name*: **BA**, *wiki*: [link](https://en.wikipedia.org/wiki/Barab%C3%A1si%E2%80%93Albert_model))

**WARNING:** in this model, some combination of parameters can generate isolated nodes. To avoid this undesired (for q-voter model) situation it is assumed that `n0 = k`!

- `N` - number of nodes.
- `n0` - initial number of nodes in the algorithm.
- `k` - number of connections for each new node.

Order of parameters in the file: `N,k`.

### Watts–Strogatz (*key name*: **WS**, *wiki*: [link](https://en.wikipedia.org/wiki/Watts%E2%80%93Strogatz_model))

- `N` - number of nodes.
- `k` - average degree of the node.
- `beta` - the probability of rewiring.

Order of parameters in the file: `N,k,beta`.

This one can create in particular a one-dimensional ring when given `k=2` and `beta=0`.

### Complete (*key name*: **C**, *wiki*: [link](https://en.wikipedia.org/wiki/Complete_graph))

- `N` - number of nodes.

Order of parameters in the file: `N`.

## Important notes

- Float **precision** standard for the app is **3 digits**.
- Average exit time uses `avg_exit_time` variables and exit probability - `exit_proba`.

## Technologies

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Julia](https://img.shields.io/badge/-Julia-9558B2?style=for-the-badge&logo=julia&logoColor=white)
![Windows Terminal](https://img.shields.io/badge/Windows%20Terminal-%234D4D4D.svg?style=for-the-badge&logo=windows-terminal&logoColor=white)

The main batch file calls a python script in a vitrual environment. However, simulations are performed in multiple processes by Julia on each available CPU. For communication, *PyJulia* module is used. Lastly, plots are created by *Seaborn*.

The newest tested versions for stable performance are:

- **Python 3.9.7**
- **Julia 1.6.1**

## Author

The project was created by [Mateusz Machaj](https://github.com/o-Mateo-o) as a tool supporting research related to his bachelor's thesis at Faculty of Pure and Applied Mathematics, Wroclaw University of Science and Technology.
