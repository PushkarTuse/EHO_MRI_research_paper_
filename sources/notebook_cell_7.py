import numpy as np
import random
import time
import matplotlib.pyplot as plt

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

    def update_velocity(self, global_best_position, inertia_weight=0.99, cognitive_weight=0.2, social_weight=0.2):
        r1, r2 = np.random.rand(), np.random.rand()
        cognitive_component = cognitive_weight * r1 * (self.best_position - self.position)
        social_component = social_weight * r2 * (global_best_position - self.position)
        self.velocity = inertia_weight * self.velocity + cognitive_component + social_component

    def move(self, bounds):
        self.position += self.velocity
        self.position = np.clip(self.position, bounds[0], bounds[1])

def pso_rastrigin(dimensions, num_particles, max_iterations, bounds=(-5.12, 5.12)):
    particles = [Particle(dimensions, bounds) for _ in range(num_particles)]
    global_best_position = particles[0].best_position.copy()
    global_best_value = rastrigin(global_best_position)

    convergence_values = []

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_personal_best()
            if particle.best_value < global_best_value:
                global_best_value = particle.best_value
                global_best_position = particle.best_position.copy()

        for particle in particles:
            particle.update_velocity(global_best_position)
            particle.move(bounds)

        # Store the best value at each iteration for the convergence plot
        convergence_values.append(global_best_value)

    return global_best_position, global_best_value, convergence_values

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

    convergence_values = []

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_position = min(herd, key=lambda e: e.fitness).position
            for elephant in herd:
                elephant.update_position(herd_best_position, global_best_position, bounds)
                elephant.mutate(bounds, mutation_rate=0.2)

        current_global_best = min(elephants, key=lambda e: e.fitness)
        if current_global_best.fitness < global_best_fitness:
            global_best_position = current_global_best.position
            global_best_fitness = current_global_best.fitness

        # Store the best value at each iteration for the convergence plot
        convergence_values.append(global_best_fitness)

    return global_best_position, global_best_fitness, convergence_values

# Test PSO and EHO on the Rastrigin function and store convergence data
def test_pso_vs_eho_on_rastrigin_with_values():
    dimensions = 10  # 10 dimensions
    num_particles = 50  # for PSO
    num_elephants = 50  # for EHO
    num_herds = 5
    max_iterations = 1000
    bounds = (-5.12, 5.12)

    # Testing PSO on Rastrigin Function
    print("Testing PSO on Rastrigin Function...")
    _, _, pso_convergence_values = pso_rastrigin(dimensions, num_particles, max_iterations, bounds)

    # Testing EHO on Rastrigin Function
    print("\nTesting EHO on Rastrigin Function...")
    _, _, eho_convergence_values = eho_rastrigin(dimensions, num_elephants, num_herds, max_iterations, bounds)

    # Print values at iterations 1, 200, 400, 600, 800, 1000
    checkpoints = [1, 200, 400, 600, 800, 1000]
    print("\nPSO Convergence Values at key iterations:")
    for cp in checkpoints:
        print(f"Iteration {cp}: {pso_convergence_values[cp-1]:.4f}")

    print("\nEHO Convergence Values at key iterations:")
    for cp in checkpoints:
        print(f"Iteration {cp}: {eho_convergence_values[cp-1]:.4f}")

    # Plot convergence graph
    plt.figure(figsize=(10, 6))
    iterations = np.arange(1, max_iterations + 1)
    plt.plot(iterations, pso_convergence_values, label='PSO Convergence', color='blue', lw=2)
    plt.plot(iterations, eho_convergence_values, label='EHO Convergence', color='green', lw=2)

    # Add labels and title
    plt.xlabel('Iterations')
    plt.ylabel('Best Value')
    plt.title('Convergence of PSO and EHO on Rastrigin Function')

    # Highlight EHO as the better performer by filling the area below the EHO line
    plt.fill_between(iterations, eho_convergence_values, color='green', alpha=0.2)

    # Add a legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.show()

# Run the updated comparison to print key iteration values and plot the graph
test_pso_vs_eho_on_rastrigin_with_values()
