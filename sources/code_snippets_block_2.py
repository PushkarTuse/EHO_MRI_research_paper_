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
    selection_probs = [f/total_fitness for f in fitness]
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

# Elephant Herding Optimization (EHO)
class Elephant:
    def __init__(self, position):
        self.position = position
        self.fitness = None

    def evaluate_fitness(self, dist_matrix):
        self.fitness = self.calculate_route_length(dist_matrix)
        return self.fitness

    def calculate_route_length(self, dist_matrix):
        total_distance = sum(dist_matrix[self.position[i]][self.position[i + 1]] for i in range(len(self.position) - 1))
        total_distance += dist_matrix[self.position[-1]][self.position[0]]  # Return to the start
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

    def move_elephants(herd, global_best):
        herd_best = min(herd, key=lambda e: e.fitness)
        for elephant in herd:
            if elephant != herd_best:
                new_position = order_crossover(elephant.position, herd_best.position)
                if random.random() < 0.2:
                    new_position = swap_mutation(new_position)
                elephant.position = new_position
                elephant.evaluate_fitness(distance_matrix)
        return min(herd, key=lambda e: e.fitness)

    def divide_into_herds(clan, num_herds):
        random.shuffle(clan)
        herd_size = len(clan) // num_herds
        return [clan[i * herd_size:(i + 1) * herd_size] for i in range(num_herds)]

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

    clan = initialize_clan(pop_size, num_cities)
    global_best = min(clan, key=lambda e: e.fitness)
    for _ in range(max_iterations):
        herds = divide_into_herds(clan, num_herds)
        for herd in herds:
            herd_best = move_elephants(herd, global_best)
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
        total_distance += distance_matrix[self.route[-1]][self.route[0]]  # Return to the start
        return total_distance

def aco_tsp(distance_matrix, num_cities, num_ants, max_iterations, alpha=1.0, beta=5.0, evaporation_rate=0.5, pheromone_init=1.0):
    pheromone_matrix = np.full((num_cities, num_cities), pheromone_init)
    best_route = None
    best_distance = float('inf')

    for iteration in range(max_iterations):
        ants = [Ant(num_cities) for _ in range(num_ants)]
        for ant in ants:
            ant.build_route(pheromone_matrix, distance_matrix, alpha, beta)
        
        # Update pheromones
        for i in range(num_cities):
            for j in range(num_cities):
                pheromone_matrix[i][j] *= (1 - evaporation_rate)
        
        for ant in ants:
            for i in range(num_cities - 1):
                pheromone_matrix[ant.route[i]][ant.route[i + 1]] += 1 / ant.distance_traveled
            pheromone_matrix[ant.route[-1]][ant.route[0]] += 1 / ant.distance_traveled
        
        # Update best route
        for ant in ants:
            if ant.distance_traveled < best_distance:
                best_distance = ant.distance_traveled
                best_route = ant.route[:]
    
    return best_route, best_distance
class Particle:
    def __init__(self, num_cities, distance_matrix):
        self.position = random.sample(range(num_cities), num_cities)  # A route
        self.best_position = self.position[:]
        self.best_distance = calculate_route_length(self.position, distance_matrix)
        self.velocity = []

    def update_personal_best(self, distance_matrix):
        current_distance = calculate_route_length(self.position, distance_matrix)
        if current_distance < self.best_distance:
            self.best_position = self.position[:]
            self.best_distance = current_distance

    def update_velocity(self, global_best_position):
        # Velocity in PSO for TSP can be viewed as a swap operation that moves particles toward global best
        self.velocity = [(a, b) for a, b in zip(self.position, global_best_position) if a != b]

    def apply_velocity(self):
        if self.velocity:
            a, b = random.choice(self.velocity)  # Choose a random swap from velocity
            self.position[a], self.position[b] = self.position[b], self.position[a]
            self.velocity.remove((a, b))

def pso_tsp(distance_matrix, num_cities, num_particles, max_iterations):
    particles = [Particle(num_cities, distance_matrix) for _ in range(num_particles)]
    global_best_position = particles[0].best_position[:]
    global_best_distance = particles[0].best_distance

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_personal_best(distance_matrix)
            if particle.best_distance < global_best_distance:
                global_best_position = particle.best_position[:]
                global_best_distance = particle.best_distance

        for particle in particles:
            particle.update_velocity(global_best_position)
            particle.apply_velocity()

    return global_best_position, global_best_distance

# Running and comparing all algorithms for 95 cities
def run_comparison_for_95_cities():
    num_cities = 95
    print(f"\nRunning for {num_cities} Cities:")

    # Generate distance matrix
    distance_matrix = generate_distance_matrix(num_cities)
    
    # GA
    start_time = time.time()
    best_route, best_distance = ga_tsp(distance_matrix, num_cities, pop_size=50, max_generations=100)
    ga_time = time.time() - start_time
    print(f"GA for {num_cities} cities: Best Distance = {best_distance}, Execution Time = {ga_time:.5f} seconds")

    # EHO
    start_time = time.time()
    best_route, best_distance = elephant_herding_optimization(distance_matrix, num_cities, pop_size=50, num_herds=5, max_iterations=100)
    eho_time = time.time() - start_time
    print(f"EHO for {num_cities} cities: Best Distance = {best_distance}, Execution Time = {eho_time:.5f} seconds")

    # ACO
    start_time = time.time()
    best_route, best_distance = aco_tsp(distance_matrix, num_cities, num_ants=10, max_iterations=100)
    aco_time = time.time() - start_time
    print(f"ACO for {num_cities} cities: Best Distance = {best_distance}, Execution Time = {aco_time:.5f} seconds")

    # PSO
    start_time = time.time()
    best_route, best_distance = pso_tsp(distance_matrix, num_cities, num_particles=10, max_iterations=100)
    pso_time = time.time() - start_time
    print(f"PSO for {num_cities} cities: Best Distance = {best_distance}, Execution Time = {pso_time:.5f} seconds")

# Running the comparison for 95 cities
run_comparison_for_95_cities()