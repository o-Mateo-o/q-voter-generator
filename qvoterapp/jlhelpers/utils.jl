"""
Basic helper functions for `NetSimul` module.
"""

"""
    allequal(arr)
Check if all the elements in the array are equal.
# Arguments
- `arr::Array`: An array of elements.
# Returns
- `::Bool`: Satisfaction of element equality condition.
"""
@inline function allequal(arr::Array{Int64,1})::Bool
    length(arr) == 1 && return true
    length(arr) == 0 && return false
    e1 = arr[1]
    i = 2
    @inbounds for i = 2:length(arr)
        arr[i] == e1 || return false
    end
    return true
end

"""
    rand_opinions(x, N)
Generate a range of random "binary" opinions.
# Arguments
- `x::Float64`: Probability of a positive opinion.
- `N::Int64`: Length of the array.
# Returns
- `::Array{Int64,1}`: Collection of the opinions (with numbers -1 or 1).
"""
@inline function rand_opinions(x::Float64, N::Int64)::Array{Int64,1}
    arr = ones(Int64, N)
    arr[1:Int64(floor((1 - x) * N))] .= -1
    return shuffle(arr)
end