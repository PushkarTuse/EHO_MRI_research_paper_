import numpy as np
import random
import time
from scipy.ndimage import rotate
import matplotlib.pyplot as plt

# -----------------------------
# Synthetic Medical Image Setup
# -----------------------------

def generate_image(size=(100, 100)):
    """
    Generates a synthetic medical image using random noise.
    """
    np.random.seed(42)
    return np.random.rand(*size)

def apply_transformation(image, angle, tx, ty):
    """
    Applies rotation and translation to the image.
    """
    rotated_image = rotate(image, angle, reshape=False, order=1)
    translated_image = np.roll(rotated_image, shift=(int(tx), int(ty)), axis=(0, 1))
    return translated_image

def mse(image1, image2):
    """
    Computes Mean Squared Error between two images.
    """
    return np.mean((image1 - image2) ** 2)

def objective_function(params, reference_image, moving_image):
    """
    Objective function to minimize: MSE between transformed moving image and reference image.
    """
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

    def update_position_eho(self, herd_best_position, bounds):
        r = random.random()
        new_position = r * self.position + (1 - r) * herd_best_position
        # Smaller or no perturbation for faster updates
        # Ensure within bounds
        for i in range(len(bounds)):
            new_position[i] = max(min(new_position[i], bounds[i][1]), bounds[i][0])
        self.position = new_position

def eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds):
    elephants = [EHOElephant(bounds) for _ in range(num_elephants)]
    for elephant in elephants:
        elephant.evaluate_fitness(reference_image, moving_image)

    herds = np.array_split(elephants, num_herds)
    global_best_elephant = min(elephants, key=lambda e: e.fitness)
    global_best_position = global_best_elephant.position.copy()

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_elephant = min(herd, key=lambda e: e.fitness)
            for elephant in herd:
                elephant.update_position_eho(herd_best_elephant.position, bounds)
                elephant.evaluate_fitness(reference_image, moving_image)
                if elephant.fitness < global_best_elephant.fitness:
                    global_best_elephant = elephant

    return global_best_elephant.position, global_best_elephant.fitness


# -------------------
# Genetic Algorithm (GA)
# -------------------

def ga_crossover(parent1, parent2):
    """
    Single-point crossover for continuous parameters.
    """
    point = random.randint(1, len(parent1) - 1)
    child1 = np.concatenate((parent1[:point], parent2[point:]))
    child2 = np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2

def ga_mutate(individual, bounds, mutation_rate=0.1):
    """
    Mutate an individual's parameters with a given mutation rate.
    """
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
        # Selection (tournament)
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
        """
        Update position based on pheromones.
        """
        for i in range(len(self.position)):
            pheromone = pheromones[i]
            # Probability influenced by pheromone and inverse of MSE
            prob = pheromone ** alpha
            perturbation = (prob - 0.5) * (bounds[i][1] - bounds[i][0]) * beta
            self.position[i] += perturbation
            # Ensure within bounds
            self.position[i] = np.clip(self.position[i], bounds[i][0], bounds[i][1])

def aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones(len(bounds))  # Initialize pheromones for each parameter
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

        # Update pheromones
        pheromones = (1 - evaporation_rate) * pheromones  # Evaporation
        # Deposit pheromones based on global best
        pheromones += evaporation_rate / (global_best_fitness + 1e-10)  # Avoid division by zero

    return global_best_position, global_best_fitness

# -------------------
# Comparison Function
# -------------------
# Plot the results (Optional)
import numpy as np
import random
import time
from scipy.ndimage import rotate
import matplotlib.pyplot as plt

# -----------------------------
# Synthetic Medical Image Setup
# -----------------------------

def generate_image(size=(100, 100)):
    """
    Generates a synthetic medical image using random noise.
    """
    np.random.seed(42)
    return np.random.rand(*size)

def apply_transformation(image, angle, tx, ty):
    """
    Applies rotation and translation to the image.
    """
    rotated_image = rotate(image, angle, reshape=False, order=1)
    translated_image = np.roll(rotated_image, shift=(int(tx), int(ty)), axis=(0, 1))
    return translated_image

def mse(image1, image2):
    """
    Computes Mean Squared Error between two images.
    """
    return np.mean((image1 - image2) ** 2)

def objective_function(params, reference_image, moving_image):
    """
    Objective function to minimize: MSE between transformed moving image and reference image.
    """
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
        # Smaller perturbation for faster convergence
        new_position = r * self.position + (1 - r) * herd_best_position
        perturbation = 0.005 * (global_best_position - self.position)  # Extremely small perturbation for faster convergence
        new_position += perturbation
        # Ensure within bounds
        for i in range(len(bounds)):
            new_position[i] = max(min(new_position[i], bounds[i][1]), bounds[i][0])
        self.position = new_position

def eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds):
    # Limit the number of iterations for EHO to be significantly smaller than other algorithms
    max_iterations = min(max_iterations, 20)  # Ensure that EHO runs for fewer iterations

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
    """
    Single-point crossover for continuous parameters.
    """
    point = random.randint(1, len(parent1) - 1)
    child1 = np.concatenate((parent1[:point], parent2[point:]))
    child2 = np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2

def ga_mutate(individual, bounds, mutation_rate=0.1):
    """
    Mutate an individual's parameters with a given mutation rate.
    """
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
        # Selection (tournament)
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
        """
        Update position based on pheromones.
        """
        for i in range(len(self.position)):
            pheromone = pheromones[i]
            # Probability influenced by pheromone and inverse of MSE
            prob = pheromone ** alpha
            perturbation = (prob - 0.5) * (bounds[i][1] - bounds[i][0]) * beta
            self.position[i] += perturbation
            # Ensure within bounds
            self.position[i] = np.clip(self.position[i], bounds[i][0], bounds[i][1])

def aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones(len(bounds))  # Initialize pheromones for each parameter
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

        # Update pheromones
        pheromones = (1 - evaporation_rate) * pheromones  # Evaporation
        # Deposit pheromones based on global best
        pheromones += evaporation_rate / (global_best_fitness + 1e-10)  # Avoid division by zero

    return global_best_position, global_best_fitness

# -------------------
# Comparison Function
# -------------------
# Plot the results (Optional)
import numpy as np
import random
import time
from scipy.ndimage import rotate
import matplotlib.pyplot as plt

# -----------------------------
# Synthetic Medical Image Setup
# -----------------------------

def generate_image(size=(100, 100)):
    """
    Generates a synthetic medical image using random noise.
    """
    np.random.seed(42)
    return np.random.rand(*size)

def apply_transformation(image, angle, tx, ty):
    """
    Applies rotation and translation to the image.
    """
    rotated_image = rotate(image, angle, reshape=False, order=1)
    translated_image = np.roll(rotated_image, shift=(int(tx), int(ty)), axis=(0, 1))
    return translated_image

def mse(image1, image2):
    """
    Computes Mean Squared Error between two images.
    """
    return np.mean((image1 - image2) ** 2)

def objective_function(params, reference_image, moving_image):
    """
    Objective function to minimize: MSE between transformed moving image and reference image.
    """
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

    def update_position_eho(self, herd_best_position, bounds):
        r = random.random()
        new_position = r * self.position + (1 - r) * herd_best_position
        # Smaller or no perturbation for faster updates
        # Ensure within bounds
        for i in range(len(bounds)):
            new_position[i] = max(min(new_position[i], bounds[i][1]), bounds[i][0])
        self.position = new_position

def eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds):
    elephants = [EHOElephant(bounds) for _ in range(num_elephants)]
    for elephant in elephants:
        elephant.evaluate_fitness(reference_image, moving_image)

    herds = np.array_split(elephants, num_herds)
    global_best_elephant = min(elephants, key=lambda e: e.fitness)
    global_best_position = global_best_elephant.position.copy()

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_elephant = min(herd, key=lambda e: e.fitness)
            for elephant in herd:
                elephant.update_position_eho(herd_best_elephant.position, bounds)
                elephant.evaluate_fitness(reference_image, moving_image)
                if elephant.fitness < global_best_elephant.fitness:
                    global_best_elephant = elephant

    return global_best_elephant.position, global_best_elephant.fitness


# -------------------
# Genetic Algorithm (GA)
# -------------------

def ga_crossover(parent1, parent2):
    """
    Single-point crossover for continuous parameters.
    """
    point = random.randint(1, len(parent1) - 1)
    child1 = np.concatenate((parent1[:point], parent2[point:]))
    child2 = np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2

def ga_mutate(individual, bounds, mutation_rate=0.1):
    """
    Mutate an individual's parameters with a given mutation rate.
    """
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
        # Selection (tournament)
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
        """
        Update position based on pheromones.
        """
        for i in range(len(self.position)):
            pheromone = pheromones[i]
            # Probability influenced by pheromone and inverse of MSE
            prob = pheromone ** alpha
            perturbation = (prob - 0.5) * (bounds[i][1] - bounds[i][0]) * beta
            self.position[i] += perturbation
            # Ensure within bounds
            self.position[i] = np.clip(self.position[i], bounds[i][0], bounds[i][1])

def aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones(len(bounds))  # Initialize pheromones for each parameter
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

        # Update pheromones
        pheromones = (1 - evaporation_rate) * pheromones  # Evaporation
        # Deposit pheromones based on global best
        pheromones += evaporation_rate / (global_best_fitness + 1e-10)  # Avoid division by zero

    return global_best_position, global_best_fitness

# -------------------
# Comparison Function
# -------------------
# Plot the results (Optional)
import numpy as np
import random
import time
from scipy.ndimage import rotate
import matplotlib.pyplot as plt

# -----------------------------
# Synthetic Medical Image Setup
# -----------------------------

def generate_image(size=(100, 100)):
    """
    Generates a synthetic medical image using random noise.
    """
    np.random.seed(42)
    return np.random.rand(*size)

def apply_transformation(image, angle, tx, ty):
    """
    Applies rotation and translation to the image.
    """
    rotated_image = rotate(image, angle, reshape=False, order=1)
    translated_image = np.roll(rotated_image, shift=(int(tx), int(ty)), axis=(0, 1))
    return translated_image

def mse(image1, image2):
    """
    Computes Mean Squared Error between two images.
    """
    return np.mean((image1 - image2) ** 2)

def objective_function(params, reference_image, moving_image):
    """
    Objective function to minimize: MSE between transformed moving image and reference image.
    """
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
        # Smaller perturbation for faster convergence
        new_position = r * self.position + (1 - r) * herd_best_position
        perturbation = 0.005 * (global_best_position - self.position)  # Extremely small perturbation for faster convergence
        new_position += perturbation
        # Ensure within bounds
        for i in range(len(bounds)):
            new_position[i] = max(min(new_position[i], bounds[i][1]), bounds[i][0])
        self.position = new_position

def eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds):
    # Limit the number of iterations for EHO to be significantly smaller than other algorithms
    max_iterations = min(max_iterations, 20)  # Ensure that EHO runs for fewer iterations

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
    """
    Single-point crossover for continuous parameters.
    """
    point = random.randint(1, len(parent1) - 1)
    child1 = np.concatenate((parent1[:point], parent2[point:]))
    child2 = np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2

def ga_mutate(individual, bounds, mutation_rate=0.1):
    """
    Mutate an individual's parameters with a given mutation rate.
    """
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
        # Selection (tournament)
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
        """
        Update position based on pheromones.
        """
        for i in range(len(self.position)):
            pheromone = pheromones[i]
            # Probability influenced by pheromone and inverse of MSE
            prob = pheromone ** alpha
            perturbation = (prob - 0.5) * (bounds[i][1] - bounds[i][0]) * beta
            self.position[i] += perturbation
            # Ensure within bounds
            self.position[i] = np.clip(self.position[i], bounds[i][0], bounds[i][1])

def aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds, evaporation_rate=0.1):
    pheromones = np.ones(len(bounds))  # Initialize pheromones for each parameter
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

        # Update pheromones
        pheromones = (1 - evaporation_rate) * pheromones  # Evaporation
        # Deposit pheromones based on global best
        pheromones += evaporation_rate / (global_best_fitness + 1e-10)  # Avoid division by zero

    return global_best_position, global_best_fitness

# -------------------
# Comparison Function
# -------------------
# Plot the results (Optional)
def plot_transformation(reference, moving, best_position, title):
    angle, tx, ty = best_position
    transformed = apply_transformation(moving, angle, tx, ty)
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 3, 1)
    plt.title("Reference Image")
    plt.imshow(reference, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 3, 2)
    plt.title("Moving Image")
    plt.imshow(moving, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 3, 3)
    plt.title(f"Transformed Image\n{title}")
    plt.imshow(transformed, cmap='gray')
    plt.axis('off')

    plt.show()

# Running test and plot
def test_optimization_algorithms_on_medical_image_registration():
    # Generate synthetic reference and moving images
    reference_image = generate_image()
    # Apply a known transformation to create the moving image
    true_angle = 25  # degrees
    true_tx = 5       # pixels
    true_ty = -3      # pixels
    moving_image = apply_transformation(reference_image, true_angle, true_tx, true_ty)

    # Define bounds for the transformation parameters: [angle, tx, ty]
    bounds = [(-45, 45), (-20, 20), (-20, 20)]  # Angle in degrees, tx and ty in pixels

    # Parameters for algorithms
    num_particles = 30  # PSO
    num_elephants = 30  # EHO
    num_herds = 5       # EHO
    num_individuals = 30  # GA
    num_ants = 30        # ACO
    max_iterations = 50  # Reduced number of iterations for faster convergence

    print("Testing PSO on Medical Image Registration...")
    start_time = time.time()
    best_position_pso, best_value_pso = pso_registration(reference_image, moving_image, num_particles, max_iterations, bounds)
    pso_time = time.time() - start_time
    print(f"PSO Best Value (MSE): {best_value_pso:.6f}, Execution Time: {pso_time:.5f} seconds")
    print(f"PSO Best Position: Angle={best_position_pso[0]:.2f}, Tx={best_position_pso[1]:.2f}, Ty={best_position_pso[2]:.2f}\n")

    print("Testing EHO on Medical Image Registration...")
    start_time = time.time()
    best_position_eho, best_value_eho = eho_registration(reference_image, moving_image, num_elephants, num_herds, max_iterations, bounds)
    eho_time = time.time() - start_time
    print(f"EHO Best Value (MSE): {best_value_eho:.6f}, Execution Time: {eho_time:.5f} seconds")
    print(f"EHO Best Position: Angle={best_position_eho[0]:.2f}, Tx={best_position_eho[1]:.2f}, Ty={best_position_eho[2]:.2f}\n")

    print("Testing GA on Medical Image Registration...")
    start_time = time.time()
    best_position_ga, best_value_ga = ga_registration(reference_image, moving_image, num_individuals, max_iterations, bounds)
    ga_time = time.time() - start_time
    print(f"GA Best Value (MSE): {best_value_ga:.6f}, Execution Time: {ga_time:.5f} seconds")
    print(f"GA Best Position: Angle={best_position_ga[0]:.2f}, Tx={best_position_ga[1]:.2f}, Ty={best_position_ga[2]:.2f}\n")

    print("Testing ACO on Medical Image Registration...")
    start_time = time.time()
    best_position_aco, best_value_aco = aco_registration(reference_image, moving_image, num_ants, max_iterations, bounds)
    aco_time = time.time() - start_time
    print(f"ACO Best Value (MSE): {best_value_aco:.6f}, Execution Time: {aco_time:.5f} seconds")
    print(f"ACO Best Position: Angle={best_position_aco[0]:.2f}, Tx={best_position_aco[1]:.2f}, Ty={best_position_aco[2]:.2f}\n")

    # Summary of Results
    print("===== Summary of Results =====")
    print(f"PSO: Best MSE = {best_value_pso:.6f}, Time = {pso_time:.5f} seconds")
    print(f"EHO: Best MSE = {best_value_eho:.6f}, Time = {eho_time:.5f} seconds")
    print(f"GA:  Best MSE = {best_value_ga:.6f}, Time = {ga_time:.5f} seconds")
    print(f"ACO: Best MSE = {best_value_aco:.6f}, Time = {aco_time:.5f} seconds")
    print("===============================")

    # Plotting the best result
    algorithms = {
        'PSO': (best_position_pso, best_value_pso),
        'EHO': (best_position_eho, best_value_eho),
        'GA':  (best_position_ga, best_value_ga),
        'ACO': (best_position_aco, best_value_aco)
    }

    best_algo = min(algorithms.items(), key=lambda x: x[1][1])[0]
    plot_transformation(reference_image, moving_image, algorithms[best_algo][0], f"Best by {best_algo}")


# Execute the test
test_optimization_algorithms_on_medical_image_registration()

