import random
import numpy as np
import time
from scipy.spatial import distance_matrix

# Generate random distance matrix for TSP
def generate_distance_matrix(num_cities):
    np.random.seed(42)
    points = np.random.rand(num_cities, 2) * 100
    return distance_matrix(points, points)

# GA Operators
def calculate_route_length(route, distance_matrix):
    return sum(distance_matrix[route[i]][route[i + 1]] for i in range(len(route) - 1)) + distance_matrix[route[-1]][route[0]]

def order_crossover(parent1, parent2):
    size = len(parent1)
    a, b = sorted(random.sample(range(size), 2))
    child = [None] * size
    child[a:b] = parent1[a:b]
    pointer = b
    for x in parent2[b:] + parent2[:b]:
        if x not in child:
            if pointer >= size:
                pointer = 0
            child[pointer] = x
            pointer += 1
    return child

def swap_mutation(route):
    a, b = random.sample(range(len(route)), 2)
    route[a], route[b] = route[b], route[a]
    return route

def initialize_population(pop_size, num_cities):
    return [random.sample(range(num_cities), num_cities) for _ in range(pop_size)]

def select_parents(population, fitness):
    total_fitness = sum(fitness)
    selection_probs = [f / total_fitness for f in fitness]
    parents = random.choices(population, weights=selection_probs, k=2)
    return parents

def ga_tsp(distance_matrix, num_cities, pop_size, max_generations, mutation_prob=0.2):
    population = initialize_population(pop_size, num_cities)
    best_route = None
    best_distance = float('inf')

    for generation in range(max_generations):
        # Calculate fitness
        fitness = [1 / calculate_route_length(ind, distance_matrix) for ind in population]

        new_population = []
        for _ in range(pop_size // 2):
            # Parent selection
            parent1, parent2 = select_parents(population, fitness)
            # Crossover
            child1 = order_crossover(parent1, parent2)
            child2 = order_crossover(parent2, parent1)
            # Mutation
            if random.random() < mutation_prob:
                child1 = swap_mutation(child1)
            if random.random() < mutation_prob:
                child2 = swap_mutation(child2)
            new_population.extend([child1, child2])

        population = new_population

        # Track the best solution
        for route in population:
            current_distance = calculate_route_length(route, distance_matrix)
            if current_distance < best_distance:
                best_distance = current_distance
                best_route = route

    return best_route, best_distance

class Elephant:
    def __init__(self, position):  # Fixed double underscores here
        self.position = position  # The current route (permutation of cities)
        self.fitness = None       # The fitness value, representing the total distance of the route

    # Evaluate fitness based on the route's total distance
    def evaluate_fitness(self, dist_matrix):
        self.fitness = self.calculate_route_length(dist_matrix)
        return self.fitness

    # Calculate the total distance of the route
    def calculate_route_length(self, dist_matrix):
        total_distance = sum(dist_matrix[self.position[i]][self.position[i + 1]] for i in range(len(self.position) - 1))
        total_distance += dist_matrix[self.position[-1]][self.position[0]]  # Return to the starting city
        return total_distance


def elephant_herding_optimization(distance_matrix, num_cities, pop_size, num_herds, max_iterations):
    def initialize_clan(pop_size, num_cities):
        clan = []
        for _ in range(pop_size):
            position = random.sample(range(num_cities), num_cities)
            elephant = Elephant(position)
            elephant.evaluate_fitness(distance_matrix)
            clan.append(elephant)
        return clan

    def move_elephants(herd, global_best, iteration, max_iterations):
        herd_best = min(herd, key=lambda e: e.fitness)
        adaptive_mutation_rate = 0.2 * (1 - iteration / max_iterations)  # Decreasing mutation rate
        for elephant in herd:
            if elephant != herd_best:
                new_position = order_crossover(elephant.position, herd_best.position)
                if random.random() < adaptive_mutation_rate:
                    new_position = swap_mutation(new_position)
                elephant.position = new_position
                elephant.evaluate_fitness(distance_matrix)
        return min(herd, key=lambda e: e.fitness)

    def divide_into_herds(clan, num_herds):
        random.shuffle(clan)
        herd_size = len(clan) // num_herds
        return [clan[i * herd_size:(i + 1) * herd_size] for i in range(num_herds)]

    # Initialize population
    clan = initialize_clan(pop_size, num_cities)
    global_best = min(clan, key=lambda e: e.fitness)

    # Start iterations
    for iteration in range(max_iterations):
        herds = divide_into_herds(clan, num_herds)
        for herd in herds:
            herd_best = move_elephants(herd, global_best, iteration, max_iterations)
            if herd_best.fitness < global_best.fitness:
                global_best = herd_best

    return global_best.position, global_best.fitness


# ACO Operators
class Ant:
    def __init__(self, num_cities):
        self.num_cities = num_cities
        self.route = []
        self.distance_traveled = 0.0

    def choose_next_city(self, current_city, unvisited_cities, pheromone_matrix, distance_matrix, alpha, beta):
        probabilities = []
        for city in unvisited_cities:
            pheromone_level = pheromone_matrix[current_city][city] ** alpha
            visibility = (1 / distance_matrix[current_city][city]) ** beta
            probabilities.append(pheromone_level * visibility)

        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]
        return np.random.choice(unvisited_cities, p=probabilities)

    def build_route(self, pheromone_matrix, distance_matrix, alpha, beta):
        self.route = []
        unvisited_cities = list(range(self.num_cities))
        current_city = random.choice(unvisited_cities)
        self.route.append(current_city)
        unvisited_cities.remove(current_city)

        while unvisited_cities:
            next_city = self.choose_next_city(current_city, unvisited_cities, pheromone_matrix, distance_matrix, alpha, beta)
            self.route.append(next_city)
            unvisited_cities.remove(next_city)
            current_city = next_city

        self.distance_traveled = self.calculate_route_length(distance_matrix)

    def calculate_route_length(self, distance_matrix):
        total_distance = sum(distance_matrix[self.route[i]][self.route[i + 1]] for i in range(self.num_cities - 1))
        total_distance += distance_matrix[self.route[-1]][self.route[0]]
        return total_distance


def aco_tsp(distance_matrix, num_cities, num_ants, max_iterations, alpha=1.0, beta=2.0, evaporation_rate=0.5, pheromone_deposit=100.0):
    pheromone_matrix = np.ones((num_cities, num_cities))
    best_route = None
    best_distance = float('inf')

    for iteration in range(max_iterations):
        ants = [Ant(num_cities) for _ in range(num_ants)]
        for ant in ants:
            ant.build_route(pheromone_matrix, distance_matrix, alpha, beta)
            if ant.distance_traveled < best_distance:
                best_distance = ant.distance_traveled
                best_route = ant.route

        # Pheromone evaporation
        pheromone_matrix *= (1 - evaporation_rate)

        # Pheromone update based on the ants' routes
        for ant in ants:
            for i in range(num_cities - 1):
                pheromone_matrix[ant.route[i]][ant.route[i + 1]] += pheromone_deposit / ant.distance_traveled
            pheromone_matrix[ant.route[-1]][ant.route[0]] += pheromone_deposit / ant.distance_traveled

    return best_route, best_distance



# PSO Operators
# PSO Operators
class Particle:
    def __init__(self, num_cities, distance_matrix):
        self.position = random.sample(range(num_cities), num_cities)  # A random route (permutation of cities)
        self.best_position = self.position[:]  # The best route the particle has encountered
        self.best_distance = calculate_route_length(self.position, distance_matrix)  # Best distance (fitness)
        self.velocity = []  # Velocity is represented as a list of swaps (changes to the permutation)

    # Update the personal best if the current route is better
    def update_personal_best(self, distance_matrix):
        current_distance = calculate_route_length(self.position, distance_matrix)
        if current_distance < self.best_distance:
            self.best_position = self.position[:]
            self.best_distance = current_distance

    # Update the velocity by determining the swaps needed to align with the global best route
    def update_velocity(self, global_best_position):
        self.velocity = []
        for i in range(len(self.position)):
            if self.position[i] != global_best_position[i]:
                swap_with_index = self.position.index(global_best_position[i])
                self.velocity.append((i, swap_with_index))

    # Apply the velocity (swaps) to update the particle's position
    def apply_velocity(self):
        for swap in self.velocity:
            i, j = swap
            self.position[i], self.position[j] = self.position[j], self.position[i]


def pso_tsp(distance_matrix, num_cities, pop_size, max_iterations):
    particles = [Particle(num_cities, distance_matrix) for _ in range(pop_size)]
    global_best_position = min(particles, key=lambda p: p.best_distance).best_position[:]
    global_best_distance = calculate_route_length(global_best_position, distance_matrix)

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_velocity(global_best_position)
            particle.apply_velocity()
            particle.update_personal_best(distance_matrix)

            if particle.best_distance < global_best_distance:
                global_best_position = particle.best_position[:]
                global_best_distance = particle.best_distance

    return global_best_position, global_best_distance

# Parameters
num_cities =20
pop_size = 20
num_herds = 20
max_generations = 100
max_iterations = 100
num_ants = 50

# Generate distance matrix
distance_matrix = generate_distance_matrix(num_cities)

# Genetic Algorithm for TSP
start_time = time.time()
best_route_ga, best_distance_ga = ga_tsp(distance_matrix, num_cities, pop_size, max_generations)
print(f"GA: Best route = {best_route_ga}, Best distance = {best_distance_ga}")
end_time = time.time()
print(start_time," ", end_time)
print(f"Execution time: {end_time - start_time} seconds")

start_time=time.time()
# Elephant Herding Optimization for TSP
best_route_eho, best_distance_eho = elephant_herding_optimization(distance_matrix, num_cities, pop_size, num_herds, max_iterations)
print(f"EHO: Best route = {best_route_eho}, Best distance = {best_distance_eho}")
end_time=time.time()
print(start_time," ", end_time)
print(f"Execution time: {end_time - start_time} seconds")

start_time=time.time()
# Ant Colony Optimization for TSP
best_route_aco, best_distance_aco = aco_tsp(distance_matrix, num_cities, num_ants, max_iterations)
print(f"ACO: Best route = {best_route_aco}, Best distance = {best_distance_aco}")
end_time=time.time()
print(start_time," ", end_time)
print(f"Execution time: {end_time - start_time} seconds")

start_time=time.time()
# Particle Swarm Optimization for TSP
best_route_pso, best_distance_pso = pso_tsp(distance_matrix, num_cities, pop_size, max_iterations)
print(f"PSO: Best route = {best_route_pso}, Best distance = {best_distance_pso}")
end_time=time.time()
print(start_time," ", end_time)
print(f"Execution time: {end_time - start_time} seconds")



# After executing all algorithms, we can store the results in arrays for plotting.
algorithms = ["GA", "EHO", "ACO", "PSO"]
execution_times = []
shortest_distances = []

# Record GA results
start_time = time.time()
best_route_ga, best_distance_ga = ga_tsp(distance_matrix, num_cities, pop_size, max_generations)
end_time = time.time()
execution_times.append(end_time - start_time)
shortest_distances.append(best_distance_ga)
print(f"GA: Best route = {best_route_ga}, Best distance = {best_distance_ga}")
print(f"Execution time: {end_time - start_time} seconds")

# Record EHO results
start_time = time.time()
best_route_eho, best_distance_eho = elephant_herding_optimization(distance_matrix, num_cities, pop_size, num_herds, max_iterations)
end_time = time.time()
execution_times.append(end_time - start_time)
shortest_distances.append(best_distance_eho)
print(f"EHO: Best route = {best_route_eho}, Best distance = {best_distance_eho}")
print(f"Execution time: {end_time - start_time} seconds")

# Record ACO results
start_time = time.time()
best_route_aco, best_distance_aco = aco_tsp(distance_matrix, num_cities, num_ants, max_iterations)
end_time = time.time()
execution_times.append(end_time - start_time)
shortest_distances.append(best_distance_aco)
print(f"ACO: Best route = {best_route_aco}, Best distance = {best_distance_aco}")
print(f"Execution time: {end_time - start_time} seconds")

# Record PSO results
start_time = time.time()
best_route_pso, best_distance_pso = pso_tsp(distance_matrix, num_cities, pop_size, max_iterations)
end_time = time.time()
execution_times.append(end_time - start_time)
shortest_distances.append(best_distance_pso)
print(f"PSO: Best route = {best_route_pso}, Best distance = {best_distance_pso}")
print(f"Execution time: {end_time - start_time} seconds")

# Now we plot the results
plt.figure(figsize=(10, 5))

# Plot Execution Time
plt.subplot(1, 2, 1)
plt.plot(algorithms, execution_times, marker='o')
plt.title('Execution Time vs Algorithms')
plt.xlabel('Algorithms')
plt.ylabel('Execution Time (seconds)')

# Plot Shortest Distance
plt.subplot(1, 2, 2)
plt.plot(algorithms, shortest_distances, marker='o', color='green')
plt.title('Shortest Distance vs Algorithms')
plt.xlabel('Algorithms')
plt.ylabel('Shortest Distance')

plt.tight_layout()
plt.show()