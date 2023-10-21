# Models

Only the models predefined in [`./src/julia/models.jl`](src/julia/models.jl) can be used. In the last definition, there is a dictionary of models' *key names*. Users should also stick to this convention of naming when creating new models.

---

Existing network models along with their parameters are:

## Barabasi-Albert (*key name*: **BA**, *wiki*: [link](https://en.wikipedia.org/wiki/Barab%C3%A1si%E2%80%93Albert_model))

**WARNING:** in this model, some combination of parameters can generate isolated nodes. To avoid this undesired (for q-voter model) situation it is assumed that `n0 = k`!

- `N` - number of nodes.
- `n0` - initial number of nodes in the algorithm.
- `k` - number of connections for each new node.

    Order of parameters in the file: `N,k`.

## Watts–Strogatz (*key name*: **WS**, *wiki*: [link](https://en.wikipedia.org/wiki/Watts%E2%80%93Strogatz_model))

- `N` - number of nodes.
- `k` - average degree of the node.
- `beta` - the probability of rewiring.

    Order of parameters in the file: `N,k,beta`.

    This one can create in particular a one-dimensional ring when given `k=2` and `beta=0`.

## Complete (*key name*: **C**, *wiki*: [link](https://en.wikipedia.org/wiki/Complete_graph))

- `N` - number of nodes.

    Order of parameters in the file: `N`.
