"""
    update!(net, q, eps)
Perform one step of a simulation.
Choose a random node and manipulate its opinion based on the *q-voter* model algorithm.
# Arguments
- `net::Net`: Structure of the desired graph model.
- `q::Int::64`: Number of considered neighbors.
- `eps::Float64`: Randomness added to the decision.
"""
function update!(net::Net, q::Int64, eps::Float64)
    v = rand(1:nv(net.graph))
    neighs = neighbors(net.graph, v)
    neighs_choice = rand(neighs, q)
    q_neigh_ops = net.opinions[neighs_choice]

    if allequal(q_neigh_ops)
        net.opinions[v] = q_neigh_ops[1]
    else
        if rand() < eps
            net.opinions[v] = -net.opinions[v]
        end
    end
end

"""
    simulate_system(net_type, x, q, ε, N, args...)
For a given set of parameters perform one Monte Carlo step of the simulation
    to find a decision time and a final state of decision.
# Arguments
- `net_type::DataType`: Type of the desired model's structure.
- `x::Float64`: Initial ratio of positive opinions.
- `q::Int64`: Number of considered neighbors.
- `eps::Float64`: Randomness added to the decision.
- `n::Int64`: Size of the system.
- `args...`: Parameters describing the system (graph).
# Returns
- `::Array{Int64,1}`: A pair of an exit time and a final state of decision. 
"""
function simulate_system(net_type::DataType, x::Float64, q::Int64, eps::Float64, N::Int64, args...)::Array{Float64,1}
    time = 0
    net = net_type(x, N, args...)
    @inbounds @fastmath while abs(sum(net.opinions)) < N
        update!(net, q, eps)
        time += 1
    end

    posit_decis = net.opinions[1] == true ? 1 : 0
    scaled_time = time / N
    return [scaled_time, posit_decis]
end

"""
    collect_system_results(x, save_path, net_type, M, q, eps, N, args...)
For a given set of parameters perform a whole Monte Carlo simulation
    to find an average decision time and a positive decision probability.
Pass the results with 3-digits precision. 
# Arguments
- `x::Float64`: Initial ratio of positive opinions.
- `save_path::String`: Database file path (relative).
- `net_type::DataType`: Type of the desired model's structure.
- `M::Int64`: Number of Monte Carlo runs.
- `q::Int64`: Number of considered neighbors.
- `eps::Float64`: Randomness added to the decision.
- `N::Int64`: Size of the system.
- `args...`: Parameters describing the system (graph).
# Returns
- `::Array{Int64,1}`: A pair of an average exit time and an exit probability. 
"""
function collect_system_results(x::Float64, net_type::DataType, M::Int64, q::Int64, eps::Float64, N::Int64, args...)
    result = [@inbounds @fastmath simulate_system(net_type, x, q, eps, N, args...) for _ = 1:M]
    av_time, p_posit_decis = [mean(hcat(result...)[param_ix, :]) for param_ix in 1:2]
    return  [round(av_time, digits=3), round(p_posit_decis, digits=3)]
end