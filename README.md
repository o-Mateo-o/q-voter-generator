# Q-voter model generator

## Plot specification (input)

```json
{   
    // FIRST PLOT
    "first.sample.plot": {
        // values related to the plot
        "plot.args": "model.x", 
        "plot.vals": "exit.proba",
        "plot.group": "model.q", // for only one group do not add this row
        // additionally `plot.valscaling` can be added
        // values related to the network
        "net.net_type": "BA",
        "net.size": 200,  // * single number value type
        "net.k": 1,  // * single number value type
        // method related value
        "method.mc_runs": 1000, // without this line, 1000 is taken on default
        // values describing the model
        "model.x": {
            // * range value type
            "start": 0,
            "step": 0.1,
            "stop": 1
        },
        "model.q": [
            // * list value type
            1,
            2,
            3
        ],
        "model.eps": 0.1
    },
    // SECOND PLOT
    "second.sample.plot": {
        "plot.args": "net.size",
        "plot.vals": "exit.time",
        "plot.group": "model.eps",
        "net.net_type": "C",
        "model.x": 0.5,
        "model.q": 4,
        // no eps & size specified before!
        "groups": [
            // it's possible to get separate sizes for each eps
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
