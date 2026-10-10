import numpy as np
import random
import time

# Rastrigin function definition
def rastrigin(position):
    n = len(position)
    return 10 * n + sum([(x ** 2 - 10 * np.cos(2 * np.pi * x)) for x in position])

# Particle class for PSO
class Particle:
    def __init__(self, dimensions, bounds):
        self.position = np.random.uniform(bounds[0], bounds[1], dimensions)
        self.velocity = np.random.uniform(bounds[0], bounds[1], dimensions)
        self.best_position = self.position.copy()
        self.best_value = rastrigin(self.position)

    def update_personal_best(self):
        current_value = rastrigin(self.position)
        if current_value < self.best_value:
            self.best_value = current_value
            self.best_position = self.position.copy()

    def update_velocity(self, global_best_position, inertia_weight=0.95, cognitive_weight=0.3, social_weight=0.3):  # Lower weights
        r1, r2 = np.random.rand(), np.random.rand()
        cognitive_component = cognitive_weight * r1 * (self.best_position - self.position)
        social_component = social_weight * r2 * (global_best_position - self.position)
        self.velocity = inertia_weight * self.velocity + cognitive_component + social_component

    def move(self, bounds):
        self.position += self.velocity
        # Ensure that the particle stays within the bounds
        self.position = np.clip(self.position, bounds[0], bounds[1])

def pso_rastrigin(dimensions, num_particles, max_iterations, bounds=(-5.12, 5.12)):
    particles = [Particle(dimensions, bounds) for _ in range(num_particles)]
    global_best_position = particles[0].best_position.copy()
    global_best_value = rastrigin(global_best_position)

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

# Elephant Herding Optimization (EHO) for Rastrigin function
class Elephant:
    def __init__(self, dimensions, bounds):
        self.position = np.random.uniform(bounds[0], bounds[1], dimensions)
        self.fitness = rastrigin(self.position)

    def update_position(self, herd_best_position, global_best_position, bounds):
        r = np.random.rand()
        new_position = r * self.position + (1 - r) * herd_best_position
        if rastrigin(new_position) < self.fitness:
            self.position = new_position
            self.fitness = rastrigin(new_position)

    # Introduce mutation to help escape local minima
    def mutate(self, bounds, mutation_rate=0.1):
        if np.random.rand() < mutation_rate:
            mutation_vector = np.random.uniform(bounds[0], bounds[1], len(self.position))
            self.position = np.clip(self.position + mutation_vector, bounds[0], bounds[1])
            self.fitness = rastrigin(self.position)

def eho_rastrigin(dimensions, num_elephants, num_herds, max_iterations, bounds=(-5.12, 5.12)):
    elephants = [Elephant(dimensions, bounds) for _ in range(num_elephants)]
    herds = np.array_split(elephants, num_herds)
    global_best_position = min(elephants, key=lambda e: e.fitness).position
    global_best_fitness = rastrigin(global_best_position)

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_position = min(herd, key=lambda e: e.fitness).position
            for elephant in herd:
                elephant.update_position(herd_best_position, global_best_position, bounds)
                elephant.mutate(bounds, mutation_rate=0.2)  # Adding mutation step

        current_global_best = min(elephants, key=lambda e: e.fitness)
        if current_global_best.fitness < global_best_fitness:
            global_best_position = current_global_best.position
            global_best_fitness = current_global_best.fitness

    return global_best_position, global_best_fitness

# Test PSO and EHO on the Rastrigin function
def test_pso_vs_eho_on_rastrigin():
    dimensions = 10  # 10 dimensions
    num_particles = 50  # for PSO
    num_elephants = 50  # for EHO
    num_herds = 5
    max_iterations = 1000
    bounds = (-5.12, 5.12)

    print("Testing PSO on Rastrigin Function...")
    start_time = time.time()
    best_position_pso, best_value_pso = pso_rastrigin(dimensions, num_particles, max_iterations, bounds)
    pso_time = time.time() - start_time
    print(f"PSO Best Value: {best_value_pso}, Execution Time: {pso_time:.5f} seconds")

    print("\nTesting EHO on Rastrigin Function...")
    start_time = time.time()
    best_position_eho, best_value_eho = eho_rastrigin(dimensions, num_elephants, num_herds, max_iterations, bounds)
    eho_time = time.time() - start_time
    print(f"EHO Best Value: {best_value_eho}, Execution Time: {eho_time:.5f} seconds")

# Run the comparison between PSO and EHO on Rastrigin function
test_pso_vs_eho_on_rastrigin()
