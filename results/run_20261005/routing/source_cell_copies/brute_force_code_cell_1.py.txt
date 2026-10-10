import itertools
import numpy as np
import time
# Generate a random distance matrix
def generate_distance_matrix(num_cities):
    np.random.seed(42)  # For reproducibility
    distance_matrix = np.random.randint(1, 100, size=(num_cities, num_cities))
    # Make it symmetric and diagonal zero (no distance to itself)
    distance_matrix = (distance_matrix + distance_matrix.T) // 2
    np.fill_diagonal(distance_matrix, 0)
    return distance_matrix

# Brute-force TSP Solver
def tsp_brute_force(distance_matrix):
    num_cities = len(distance_matrix)
    cities = list(range(num_cities))

    # Initialize the minimum distance to infinity
    min_distance = float('inf')
    best_route = None

    # Try every permutation of the cities
    for perm in itertools.permutations(cities):
        current_distance = 0

        # Calculate total distance for this route
        for i in range(num_cities - 1):
            current_distance += distance_matrix[perm[i]][perm[i + 1]]
        current_distance += distance_matrix[perm[-1]][perm[0]]  # Return to the start

        # Update the best route if the current distance is smaller
        if current_distance < min_distance:
            min_distance = current_distance
            best_route = perm
        print(current_distance,min_distance)

    return best_route, min_distance

# Main function to test TSP brute-force
def main():
    start_time=time.time()
    num_cities = 20  # Number of cities (nodes)
    distance_matrix = [[0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
    [15, 35, 0, 30, 12, 12, 43, 45, 64, 65 ],  # Distances from city C
    [20, 25, 30, 0, 45, 65, 64, 46, 23, 45],
                       [0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
    [15, 35, 0, 30, 12, 12, 43, 45, 64, 65 ],  # Distances from city C
    [20, 25, 30, 0, 45, 65, 64, 46, 23, 45],[0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
   ]


    print("Distance Matrix:")
    print(distance_matrix)

    # Solve TSP
    best_route, min_distance = tsp_brute_force(distance_matrix)

    print("\nBest route:", best_route)
    print("Minimum distance:", min_distance)
    end_time=time.time()
    print(f"Execution time: {end_time-start_time}")
# Run the TSP brute-force solution
if __name__ == "__main__":
    main()
