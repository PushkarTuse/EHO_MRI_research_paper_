import random
import numpy as np
import copy
import time
# Define the number of cities
NUM_CITIES = 10


DISTANCE_MATRIX = [[0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
    [15, 35, 0, 30, 12, 12, 43, 45, 64, 65 ],  # Distances from city C
    [20, 25, 30, 0, 45, 65, 64, 46, 23, 45],
                       [0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
    [15, 35, 0, 30, 12, 12, 43, 45, 64, 65 ],  # Distances from city C
    [20, 25, 30, 0, 45, 65, 64, 46, 23, 45],[0, 10, 15, 20, 25, 30, 31, 42, 32, 43],  # Distances from city A
    [10, 0, 35, 25, 23, 23, 43, 34, 43, 43, 23],  # Distances from city B
   ]


# Elephant class
class Elephant:
    def __init__(self, position, cooperative_value, competitive_value):
        self.position = position  # A permutation representing a TSP route
        self.cooperative_value = cooperative_value
        self.competitive_value = competitive_value
        self.fitness = None  # To be calculated based on the TSP route length

    def evaluate_fitness(self):
        self.fitness = self.calculate_route_length()
        return self.fitness

    def calculate_route_length(self):
        total_distance = 0
        for i in range(len(self.position) - 1):
            total_distance += DISTANCE_MATRIX[self.position[i]][self.position[i + 1]]
        # Return to the starting city
        total_distance += DISTANCE_MATRIX[self.position[-1]][self.position[0]]
        return total_distance

# Initialize clan (population of elephants)
def initialize_clan(pop_size, num_cities):
    clan = []
    for _ in range(pop_size):
        position = random.sample(range(num_cities), num_cities)  # Random permutation
        cooperative_value = random.uniform(0.0, 1.0)
        competitive_value = random.uniform(0.0, 1.0)
        elephant = Elephant(position, cooperative_value, competitive_value)
        elephant.evaluate_fitness()
        clan.append(elephant)
    return clan

# Divide the clan into herds
def divide_into_herds(clan, num_herds):
    random.shuffle(clan)
    herd_size = len(clan) // num_herds
    herds = [clan[i * herd_size:(i + 1) * herd_size] for i in range(num_herds)]
    # Handle any remaining elephants
    for i, elephant in enumerate(clan[num_herds * herd_size:]):
        herds[i % num_herds].append(elephant)
    return herds

# Crossover operator for permutations
def order_crossover(parent1, parent2):
    size = len(parent1)
    a, b = sorted(random.sample(range(size), 2))
    child = [None]*size
    child[a:b] = parent1[a:b]
    pointer = b
    for x in parent2[b:] + parent2[:b]:
        if x not in child:
            if pointer >= size:
                pointer = 0
            child[pointer] = x
            pointer +=1
    return child

# Mutation operator for permutations
def swap_mutation(route):
    a, b = random.sample(range(len(route)), 2)
    route[a], route[b] = route[b], route[a]
    return route

# Move elephants towards the herd best and global best
def move_elephants(herd, global_best):
    herd_best = min(herd, key=lambda e: e.fitness)
    for elephant in herd:
        if elephant != herd_best:
            # Crossover with herd best
            new_position = order_crossover(elephant.position, herd_best.position)
            # Mutation
            if random.random() < 0.2:  # Mutation probability
                new_position = swap_mutation(new_position)
            # Update elephant's position and fitness
            elephant.position = new_position
            elephant.evaluate_fitness()
    # Update herd best
    herd_best = min(herd, key=lambda e: e.fitness)
    # Move herd best towards global best
    if herd_best.fitness > global_best.fitness:
        # Crossover with global best
        new_position = order_crossover(herd_best.position, global_best.position)
        # Mutation
        if random.random() < 0.2:
            new_position = swap_mutation(new_position)
        herd_best.position = new_position
        herd_best.evaluate_fitness()
    return herd_best

# Main EHO algorithm
def elephant_herding_optimization(num_cities, pop_size, num_herds, max_iterations):
    # Initialize clan
    clan = initialize_clan(pop_size, num_cities)
    # Evaluate initial global best
    global_best = min(clan, key=lambda e: e.fitness)
    fitness_history = []

    for iteration in range(max_iterations):
        # Divide into herds
        herds = divide_into_herds(clan, num_herds)
        # Move elephants in each herd
        for herd in herds:
            herd_best = move_elephants(herd, global_best)
            # Update global best
            if herd_best.fitness < global_best.fitness:
                global_best = copy.deepcopy(herd_best)
        # Record fitness
        fitness_history.append(global_best.fitness)
        print(f"Iteration {iteration + 1}, Best Fitness: {global_best.fitness}")
        # Check for convergence (optional)
        if iteration > 10 and all(fitness_history[-1] == f for f in fitness_history[-10:]):
            print("Convergence reached.")
            break
    return global_best

# Run the EHO algorithm for TSP
def main():
    start_time = time.time()
    NUM_CITIES = 10
    POP_SIZE = 50
    NUM_HERDS = 10
    MAX_ITERATIONS = 7

    best_elephant = elephant_herding_optimization(NUM_CITIES, POP_SIZE, NUM_HERDS, MAX_ITERATIONS)
    print("\nBest Route Found:")
    print(best_elephant.position)
    print(f"Minimum Distance: {best_elephant.fitness}")
    end_time = time.time()
    print(f"Execution time: {end_time - start_time}")
if __name__ == "__main__":
    main()
+