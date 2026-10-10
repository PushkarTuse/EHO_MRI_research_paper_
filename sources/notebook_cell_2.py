import numpy as np
import random
import time
from math import exp, sqrt, cos, pi

# Ackley function definition
def ackley(position):
    a = 20
    b = 0.2
    c = 2 * pi
    n = len(position)
    sum1 = sum([x**2 for x in position])
    sum2 = sum([cos(c * x) for x in position])
    term1 = -a * exp(-b * sqrt(sum1 / n))
    term2 = -exp(sum2 / n)
    return term1 + term2 + a + exp(1)

# Particle Swarm Optimization (PSO)
class Particle:
    def __init__(self, dimensions, bounds):
        self.position = np.random.uniform(bounds[:, 0], bounds[:, 1], dimensions)
        self.velocity = np.random.uniform(bounds[:, 0], bounds[:, 1], dimensions)
        self.best_position = self.position.copy()
        self.best_value = ackley(self.position)

    def update_personal_best(self):
        current_value = ackley(self.position)
        if current_value < self.best_value:
            self.best_value = current_value
            self.best_position = self.position.copy()

    def update_velocity(self, global_best_position, inertia_weight=0.7, cognitive_weight=1.5, social_weight=1.5):
        r1, r2 = np.random.rand(), np.random.rand()
        cognitive_component = cognitive_weight * r1 * (self.best_position - self.position)
        social_component = social_weight * r2 * (global_best_position - self.position)
        self.velocity = inertia_weight * self.velocity + cognitive_component + social_component

    def move(self, bounds):
        self.position += self.velocity
        self.position = np.clip(self.position, bounds[:, 0], bounds[:, 1])

def pso_ackley(dimensions, num_particles, max_iterations, bounds):
    particles = [Particle(dimensions, bounds) for _ in range(num_particles)]
    global_best_position = particles[0].best_position.copy()
    global_best_value = ackley(global_best_position)

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_personal_best()
            if particle.best_value < global_best_value:
                global_best_value = particle.best_value
                global_best_position = particle.best_position.copy()

        for particle in particles:
            particle.update_velocity(global_best_position)
            particle.move(bounds)

    return global_best_position, global_best_value

# Improved Elephant Herding Optimization (EHO)
class Elephant:
    def __init__(self, dimensions, bounds):
        self.position = np.random.uniform(bounds[:, 0], bounds[:, 1], dimensions)
        self.velocity = np.random.uniform(bounds[:, 0], bounds[:, 1], dimensions)
        self.fitness = ackley(self.position)

    def update_position(self, herd_best_position, bounds, iteration, max_iterations):
        r = np.random.rand()
        inertia_weight = 0.9 - 0.5 * (iteration / max_iterations)  # Decreasing inertia weight
        self.velocity = inertia_weight * self.velocity + np.random.rand() * (herd_best_position - self.position)
        new_position = self.position + self.velocity
        self.position = np.clip(new_position, bounds[:, 0], bounds[:, 1])
        self.fitness = ackley(self.position)

    def mutate(self, bounds, mutation_rate):
        if np.random.rand() < mutation_rate:
            mutation_vector = np.random.uniform(bounds[:, 0], bounds[:, 1], len(self.position))
            self.position = np.clip(self.position + mutation_vector, bounds[:, 0], bounds[:, 1])
        self.fitness = ackley(self.position)

def eho_ackley(dimensions, num_elephants, num_herds, max_iterations, bounds):
    elephants = [Elephant(dimensions, bounds) for _ in range(num_elephants)]
    global_best_position = min(elephants, key=lambda e: e.fitness).position
    global_best_fitness = ackley(global_best_position)

    for iteration in range(max_iterations):
        dynamic_herds = int(num_herds - (num_herds - 1) * (iteration / max_iterations))  # Reduce herd size over time
        herds = np.array_split(elephants, dynamic_herds)
        dynamic_mutation_rate = 0.2 * (1 - iteration / max_iterations)  # Decrease mutation rate over time

        for herd in herds:
            herd_best_position = min(herd, key=lambda e: e.fitness).position
            for elephant in herd:
                elephant.update_position(herd_best_position, bounds, iteration, max_iterations)
                elephant.mutate(bounds, dynamic_mutation_rate)

        # Update global best elephant
        current_global_best = min(elephants, key=lambda e: e.fitness)
        if current_global_best.fitness < global_best_fitness:
            global_best_position = current_global_best.position
            global_best_fitness = current_global_best.fitness

    return global_best_position, global_best_fitness

# Genetic Algorithm (GA)
def ga_ackley(dimensions, num_individuals, max_generations, bounds, mutation_prob=0.2):
    def crossover(parent1, parent2):
        point = np.random.randint(1, len(parent1) - 1)
        child1 = np.concatenate((parent1[:point], parent2[point:]))
        child2 = np.concatenate((parent2[:point], parent1[point:]))
        return child1, child2

    def mutate(individual):
        mutation_point = np.random.randint(len(individual))
        individual[mutation_point] = np.random.uniform(bounds[mutation_point, 0], bounds[mutation_point, 1])
        return individual

    population = [np.random.uniform(bounds[:, 0], bounds[:, 1], dimensions) for _ in range(num_individuals)]
    best_individual = min(population, key=lambda ind: ackley(ind))
    best_value = ackley(best_individual)

    for generation in range(max_generations):
        new_population = []
        for i in range(num_individuals // 2):
            parent1, parent2 = random.choices(population, k=2)
            child1, child2 = crossover(parent1, parent2)
            if np.random.rand() < mutation_prob:
                child1 = mutate(child1)
            if np.random.rand() < mutation_prob:
                child2 = mutate(child2)
            new_population.extend([child1, child2])

        population = new_population
        best_candidate = min(population, key=lambda ind: ackley(ind))
        best_candidate_value = ackley(best_candidate)
        if best_candidate_value < best_value:
            best_individual = best_candidate
            best_value = best_candidate_value

    return best_individual, best_value

# Ant Colony Optimization (ACO)
class Ant:
    def __init__(self, bounds):
        self.position = np.random.uniform(bounds[:, 0], bounds[:, 1])
        self.fitness = ackley(self.position)

    def update_position(self, pheromones, bounds, alpha=1.0, beta=1.0):
        for i in range(len(self.position)):
            pheromone_level = pheromones[i][0]  # Ensure we treat pheromone as a scalar
            attraction = pheromone_level ** alpha
            exploration = (1 / (np.abs(bounds[i, 1] - bounds[i, 0]))) ** beta
            perturbation = (attraction - 0.5) * exploration
            self.position[i] += perturbation

            # Ensure the position stays within bounds
            self.position[i] = np.clip(self.position[i], bounds[i, 0], bounds[i, 1])

def aco_ackley(dimensions, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones((len(bounds), 1))  # Initialize pheromones for each parameter (angle, tx, ty)
    ants = [Ant(bounds) for _ in range(num_ants)]
    global_best_position = ants[0].position.copy()
    global_best_value = float('inf')

    for iteration in range(max_iterations):
        # Move ants and evaluate fitness
        for ant in ants:
            ant.update_position(pheromones, bounds)
            fitness = ackley(ant.position)
            if fitness < global_best_value:
                global_best_position = ant.position.copy()
                global_best_value = fitness

        # Update pheromones based on the global best
        for i in range(len(pheromones)):
            pheromones[i] = (1 - evaporation_rate) * pheromones[i] + evaporation_rate * global_best_value

    return global_best_position, global_best_value

# Run the comparison between PSO, EHO, GA, and ACO for the Ackley function
def test_optimization_algorithms_on_ackley():
    dimensions = 10  # Ackley function in 10 dimensions
    num_particles = 50  # for PSO
    num_elephants = 50  # for EHO
    num_herds = 5       # for EHO
    num_individuals = 50  # for GA
    num_ants = 50        # for ACO
    max_iterations = 100  # Maximum iterations/generations
    bounds = np.array([[-32.768, 32.768]] * dimensions)  # Typical bounds for Ackley function

    print("Testing PSO on Ackley Function...")
    start_time = time.time()
    best_position_pso, best_value_pso = pso_ackley(dimensions, num_particles, max_iterations, bounds)
    pso_time = time.time() - start_time
    print(f"PSO Best Value (Ackley): {best_value_pso}, Execution Time: {pso_time:.5f} seconds")

    print("\nTesting Improved EHO on Ackley Function...")
    start_time = time.time()
    best_position_eho, best_value_eho = eho_ackley(dimensions, num_elephants, num_herds, max_iterations, bounds)
    eho_time = time.time() - start_time
    print(f"EHO Best Value (Ackley): {best_value_eho}, Execution Time: {eho_time:.5f} seconds")

    print("\nTesting GA on Ackley Function...")
    start_time = time.time()
    best_position_ga, best_value_ga = ga_ackley(dimensions, num_individuals, max_iterations, bounds)
    ga_time = time.time() - start_time
    print(f"GA Best Value (Ackley): {best_value_ga}, Execution Time: {ga_time:.5f} seconds")

    print("\nTesting ACO on Ackley Function...")
    start_time = time.time()
    best_position_aco, best_value_aco = aco_ackley(dimensions, num_ants, max_iterations, bounds)
    aco_time = time.time() - start_time
    print(f"ACO Best Value (Ackley): {best_value_aco}, Execution Time: {aco_time:.5f} seconds")

    # Show a comparison of results
    print("\nSummary of Results:")
    print(f"PSO: Best Value = {best_value_pso}, Time = {pso_time:.5f} seconds")
    print(f"EHO: Best Value = {best_value_eho}, Time = {eho_time:.5f} seconds")
    print(f"GA:  Best Value = {best_value_ga}, Time = {ga_time:.5f} seconds")
    print(f"ACO: Best Value = {best_value_aco}, Time = {aco_time:.5f} seconds")

# Run the comparison of optimization algorithms on the Ackley function
test_optimization_algorithms_on_ackley()
