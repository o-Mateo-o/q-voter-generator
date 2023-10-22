using Pkg

dependencies = [
    "Graphs",
    "Distributions",
    "Random",
    "Statistics",
    "PyCall"
]

function ensure_packages()
    not_installed_message_flag = true
    isinstalled(pkg::String) = any(x -> x.name == pkg && x.is_direct_dep, values(Pkg.dependencies()))

    for dependency in dependencies
        if !isinstalled(dependency)
            if not_installed_message_flag
                println("Some Julia packages are not yet installed. Please wait... ")
            end
            global not_installed_message_flag = false
            Pkg.add(dependency)
        end
    end

    if !not_installed_message_flag
        println("Julia packages ready for using NetSimul module!")
    end
end