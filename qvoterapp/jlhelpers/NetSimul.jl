"""
Module providing the fine tools for q-voter simulations on various graph models.
"""

__precompile__()


module NetSimul
export examine_q_voter

using Graphs
using Distributions, Random, Statistics

include("utils.jl")
include("models.jl")
include("simulations.jl")


"""
    examine_q_voter(x, net_key, M, q, eps, N, args...)
For a given set of parameters perform a whole Monte Carlo simulation
    to find an average decision time and a positive decision probability. 
# Arguments
- `x::Float64`: Initial ratio of positive opinions.
- `net_key::String`: Type of the desired model's structure.
- `M::Int64`: Number of Monte Carlo runs.
- `q::Int64`: Number of considered neighbors.
- `eps::Float64`: Randomness added to the decision.
- `N::Int64`: Size of the system.
- `args...`: Parameters describing the system (graph).
# Returns
- `::Array{Int64,1}`: A pair of an average exit time and an exit probability.
"""
function examine_q_voter(x::Float64, net_key::String, M::Int64, q::Int64, eps::Float64, N::Int64, args...)
    return collect_system_results(x, model_dict[net_key], M, q, eps, N, args...)
end

end