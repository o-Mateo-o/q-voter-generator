# Q-voter model generator

![GitHub last commit](https://img.shields.io/github/last-commit/o-Mateo-o/q-voter-generator)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) [![Licence](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=for-the-badge)](./LICENSE)

## Table of contents

## Description

### Structure

<!-- sth about data as well -->

## Usage

### Quick guide

1. xxx
2. asd
3. asd

   ```batch
   asd
   ```

### Help

### *One-clicker* execution

## JSON specification file

### Rules

### Example

```python
{   
    # FIRST PLOT
    "first.sample.plot": {
        # values related to the plot
        "plot.args": "model.x", 
        "plot.vals": "exit.proba",
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
        "plot.vals": "exit.time",
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

## Technologies

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Julia](https://img.shields.io/badge/-Julia-9558B2?style=for-the-badge&logo=julia&logoColor=white) ![Windows Terminal](https://img.shields.io/badge/Windows%20Terminal-%234D4D4D.svg?style=for-the-badge&logo=windows-terminal&logoColor=white)

- asa
- asd

## Author
