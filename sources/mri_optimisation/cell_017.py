import numpy as np
import random
import time
from scipy.ndimage import rotate
import matplotlib.pyplot as plt

# -----------------------------
# Synthetic Medical Image Setup
# -----------------------------

def generate_image(size=(100, 100)):
    """Generates a synthetic medical image using random noise."""
    np.random.seed(42)
    return np.random.rand(*size)

def apply_transformation(image, angle, tx, ty):
    """Applies rotation and translation to the image."""
    rotated_image = rotate(image, angle, reshape=False, order=1)
    translated_image = np.roll(rotated_image, shift=(int(tx), int(ty)), axis=(0, 1))
    return translated_image

def mse(image1, image2):
    """Computes Mean Squared Error between two images."""
    return np.mean((image1 - image2) ** 2)

def objective_function(params, reference_image, moving_image):
    """Objective function to minimize: MSE between transformed moving image and reference image."""
    angle, tx, ty = params
    transformed_image = apply_transformation(moving_image, angle, tx, ty)
    return mse(reference_image, transformed_image)

# -------------------
# Particle Swarm (PSO)
# -------------------

class PSOParticle:
    def __init__(self, bounds):
        self.position = np.array([random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))])
        self.velocity = np.array([random.uniform(-abs(bounds[i][1] - bounds[i][0]), abs(bounds[i][1] - bounds[i][0])) for i in range(len(bounds))])
        self.best_position = self.position.copy()
        self.best_value = float('inf')

    def update_personal_best(self, reference_image, moving_image):
        current_value = objective_function(self.position, reference_image, moving_image)
        if current_value < self.best_value:
            self.best_value = current_value
            self.best_position = self.position.copy()

    def update_velocity_pso(self, global_best_position, inertia_weight=0.7, cognitive_weight=1.5, social_weight=1.5):
        r1, r2 = random.random(), random.random()
        cognitive_component = cognitive_weight * r1 * (self.best_position - self.position)
        social_component = social_weight * r2 * (global_best_position - self.position)
        self.velocity = inertia_weight * self.velocity + cognitive_component + social_component

    def move_pso(self, bounds):
        self.position += self.velocity
        # Ensure the particle stays within bounds
        for i in range(len(bounds)):
            if self.position[i] < bounds[i][0]:
                self.position[i] = bounds[i][0]
                self.velocity[i] = 0
            elif self.position[i] > bounds[i][1]:
                self.position[i] = bounds[i][1]
                self.velocity[i] = 0

def pso_registration(reference_image, moving_image, num_particles, max_iterations, bounds):
    particles = [PSOParticle(bounds) for _ in range(num_particles)]
    global_best_position = particles[0].best_position.copy()
    global_best_value = float('inf')

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_personal_best(reference_image, moving_image)
            if particle.best_value < global_best_value:
                global_best_value = particle.best_value
                global_best_position = particle.best_position.copy()

        for particle in particles:
            particle.update_velocity_pso(global_best_position)
            particle.move_pso(bounds)

    return global_best_position, global_best_value

# -------------------
# Elephant Herding (EHO)
# -------------------

class EHOElephant:
    def __init__(self, bounds):
        self.position = np.array([random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))])
        self.fitness = float('inf')

    def evaluate_fitness(self, reference_image, moving_image):
        self.fitness = objective_function(self.position, reference_image, moving_image)

    def update_position_eho(self, herd_best_position, global_best_position, bounds):
        r = random.random()
        new_position = r * self.position + (1 - r) * herd_best_position
        perturbation = 0.005 * (global_best_position - self.position)  # Extremely small perturbation for faster convergence
        new_position += perturbation
        for i in range(len(bounds)):
            new_position[i] = max(min(new_position[i], bounds[i][1]), bounds[i][0])
        self.position = new_position

def eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds):
    max_iterations = min(max_iterations, 20)  # EHO runs for fewer iterations
    elephants = [EHOElephant(bounds) for _ in range(num_elephants)]
    for elephant in elephants:
        elephant.evaluate_fitness(reference_image, moving_image)

    herds = np.array_split(elephants, num_herds)
    global_best_elephant = min(elephants, key=lambda e: e.fitness)
    global_best_position = global_best_elephant.position.copy()
    global_best_fitness = global_best_elephant.fitness

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_elephant = min(herd, key=lambda e: e.fitness)
            for elephant in herd:
                elephant.update_position_eho(herd_best_elephant.position, global_best_position, bounds)
                elephant.evaluate_fitness(reference_image, moving_image)
                if elephant.fitness < global_best_fitness:
                    global_best_fitness = elephant.fitness
                    global_best_position = elephant.position.copy()

    return global_best_position, global_best_fitness

# -------------------
# Genetic Algorithm (GA)
# -------------------

def ga_crossover(parent1, parent2):
    """Single-point crossover for continuous parameters."""
    point = random.randint(1, len(parent1) - 1)
    child1 = np.concatenate((parent1[:point], parent2[point:]))
    child2 = np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2

def ga_mutate(individual, bounds, mutation_rate=0.1):
    """Mutate an individual's parameters with a given mutation rate."""
    for i in range(len(individual)):
        if random.random() < mutation_rate:
            individual[i] = random.uniform(bounds[i][0], bounds[i][1])
    return individual

def ga_registration(reference_image, moving_image, num_individuals, max_generations, bounds, mutation_rate=0.1):
    population = [np.array([random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]) for _ in range(num_individuals)]
    fitness = [objective_function(ind, reference_image, moving_image) for ind in population]
    best_idx = np.argmin(fitness)
    best_individual = population[best_idx].copy()
    best_fitness = fitness[best_idx]

    for generation in range(max_generations):
        new_population = []
        for _ in range(num_individuals // 2):
            parent1, parent2 = random.sample(population, 2)
            child1, child2 = ga_crossover(parent1, parent2)
            child1 = ga_mutate(child1, bounds, mutation_rate)
            child2 = ga_mutate(child2, bounds, mutation_rate)
            new_population.extend([child1, child2])

        population = new_population
        fitness = [objective_function(ind, reference_image, moving_image) for ind in population]
        current_best_idx = np.argmin(fitness)
        current_best_fitness = fitness[current_best_idx]
        if current_best_fitness < best_fitness:
            best_fitness = current_best_fitness
            best_individual = population[current_best_idx].copy()

    return best_individual, best_fitness

# -------------------
# Ant Colony Optimization (ACO)
# -------------------

class ACOAnt:
    def __init__(self, bounds):
        self.position = np.array([random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))])
        self.fitness = float('inf')

    def move_position(self, pheromones, bounds, alpha=1.0, beta=1.0):
        for i in range(len(self.position)):
            pheromone = pheromones[i]
            prob = pheromone ** alpha
            perturbation = (prob - 0.5) * (bounds[i][1] - bounds[i][0]) * beta
            self.position[i] += perturbation
            self.position[i] = np.clip(self.position[i], bounds[i][0], bounds[i][1])

def aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones(len(bounds))
    ants = [ACOAnt(bounds) for _ in range(num_ants)]
    global_best_position = ants[0].position.copy()
    global_best_fitness = float('inf')

    for iteration in range(max_iterations):
        for ant in ants:
            ant.move_position(pheromones, bounds)
            ant.fitness = objective_function(ant.position, reference_image, moving_image)
            if ant.fitness < global_best_fitness:
                global_best_fitness = ant.fitness
                global_best_position = ant.position.copy()

        pheromones = (1 - evaporation_rate) * pheromones  # Evaporation
        pheromones += evaporation_rate / (global_best_fitness + 1e-10)  # Deposit based on global best fitness

    return global_best_position, global_best_fitness

# -------------------
# Comparison Function and Dataset Expansion
# -------------------

def run_experiment_with_increasing_datasets(num_images_list):
    times_pso = []
    times_eho = []
    times_ga = []
    times_aco = []

    for num_images in num_images_list:
        print(f"Running experiment with {num_images} images...")

        # Generate dataset of multiple images
        reference_images = [generate_image() for _ in range(num_images)]
        moving_images = [apply_transformation(img, 25, 5, -3) for img in reference_images]
        bounds = [(-45, 45), (-20, 20), (-20, 20)]

        num_particles = 30
        num_elephants = 30
        num_herds = 5
        num_individuals = 30
        num_ants = 30
        max_iterations = 50

        # ------------------ PSO ------------------
        start_time = time.time()
        for ref_img, mov_img in zip(reference_images, moving_images):
            pso_registration(ref_img, mov_img, num_particles, max_iterations, bounds)
        times_pso.append(time.time() - start_time)

        # ------------------ EHO ------------------
        start_time = time.time()
        for ref_img, mov_img in zip(reference_images, moving_images):
            eho_registration(ref_img, mov_img, num_elephants, num_herds, max_iterations, bounds)
        times_eho.append(time.time() - start_time)

        # ------------------ GA ------------------
        start_time = time.time()
        for ref_img, mov_img in zip(reference_images, moving_images):
            ga_registration(ref_img, mov_img, num_individuals, max_iterations, bounds)
        times_ga.append(time.time() - start_time)

        # ------------------ ACO ------------------
        start_time = time.time()
        for ref_img, mov_img in zip(reference_images, moving_images):
            aco_registration(ref_img, mov_img, num_ants, max_iterations, bounds)
        times_aco.append(time.time() - start_time)

    # Plot the results
    plot_execution_time_vs_dataset_size(num_images_list, times_pso, times_eho, times_ga, times_aco)

def plot_execution_time_vs_dataset_size(dataset_sizes, times_pso, times_eho, times_ga, times_aco):
    plt.figure(figsize=(10, 6))
    plt.plot(dataset_sizes, times_pso, label='PSO', marker='o')
    plt.plot(dataset_sizes, times_eho, label='EHO', marker='o')
    plt.plot(dataset_sizes, times_ga, label='GA', marker='o')
    plt.plot(dataset_sizes, times_aco, label='ACO', marker='o')

    plt.title('Execution Time vs Dataset Size')
    plt.xlabel('Dataset Size (Number of Images)')
    plt.ylabel('Execution Time (seconds)')
    plt.legend()
    plt.grid(True)
    plt.show()

# -------------------
# Main Execution
# -------------------

# Run experiment with increasing number of images in the dataset
dataset_sizes = [10, 20, 30, 40, 50]  # You can adjust these values as needed
run_experiment_with_increasing_datasets(dataset_sizes)

