"""
Predefined graph models.
"""

abstract type Net end

"""
`NetBA` is Barabasi-Albert social network with opinions descriptions.

**WARNING:** `n0` (initial number of nodes) = `k` (new connections coefficient)
for the sake of isolated units issue - not accepted in the simulation model!

# Fields
- `graph::SimpleGraph{Int64}`: Graph representation of the system (nodes and edges).
- `opinions::Array{Int64}`: List of opinions assigned to nodes.
- ``
# Arguments
- `x::Float64`: Proportion of positive opinions in the system.
- `N::Int64`: Size of the system.
- `k::Int64`: Initial number of nodes; new connections coefficient.
"""
struct NetBA <: Net
    graph::SimpleGraph{Int64}
    opinions::Array{Int64}
    NetBA(x::Float64, N::Int64, k::Int64) = new(barabasi_albert(N, k, k), rand_opinions(x, N))
end

"""
`NetWS` is Watts-Strogatz social network with opinions description.
# Fields
- `graph::SimpleGraph{Int64}`: Graph representation of the system (nodes and edges).
- `opinions::Array{Int64}`: List of opinions assigned to nodes.
- ``
# Arguments
- `x::Float64`: Proportion of positive opinions in the system.
- `N::Int64`: Size of the system.
- `k::Int64`: Mean node degree.
- `beta::Float64`: Rewiring probability.
"""
struct NetWS <: Net
    graph::SimpleGraph{Int64}
    opinions::Array{Int64}
    NetWS(x::Float64, N::Int64, k::Int64, beta::Float64) = new(watts_strogatz(N, k, beta), rand_opinions(x, N))
end

"""
`NetC` is a complete (fully connected) social network with opinions description.
# Fields
- `graph::SimpleGraph{Int64}`: Graph representation of the system (nodes and edges).
- `opinions::Array{Int64}`: List of opinions assigned to nodes.
- ``
# Arguments
- `x::Float64`: Proportion of positive opinions in the system.
- `N::Int64`: Size of the system.
"""
struct NetC <: Net
    graph::SimpleGraph{Int64}
    opinions::Array{Int64}
    NetC(x::Float64, N::Int64) = new(complete_graph(N), rand_opinions(x, N))
end

"""
Model structures assigned to the key names.
"""
const model_dict = Dict("BA" => NetBA, "WS" => NetWS, "C" => NetC)