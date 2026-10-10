import numpy as np
import random
import time

# Particle Swarm Optimization (PSO) for VRP
class Particle:
    def __init__(self, num_customers, num_vehicles, capacity, customer_demands, dist_matrix):
        self.num_customers = num_customers
        self.num_vehicles = num_vehicles
        self.capacity = capacity
        self.customer_demands = customer_demands
        self.dist_matrix = dist_matrix
        self.routes = self.initialize_routes()
        self.velocity = self.initialize_velocity()
        self.best_position = [route[:] for route in self.routes]  # Deep copy to avoid reference issues
        self.best_value = vrp_cost(self.routes, self.dist_matrix)

    def initialize_routes(self):
        customers = list(range(1, self.num_customers + 1))
        random.shuffle(customers)
        routes = []
        for _ in range(self.num_vehicles):
            route = []
            total_load = 0
            while customers and total_load + self.customer_demands[customers[0]] <= self.capacity:
                customer = customers.pop(0)
                route.append(customer)
                total_load += self.customer_demands[customer]
            routes.append(route)
        return routes

    def initialize_velocity(self):
        # Velocity has the same structure as routes but with random scalar movement
        return [np.random.uniform(-1, 1, size=len(route)) for route in self.routes]

    def update_personal_best(self):
        current_value = vrp_cost(self.routes, self.dist_matrix)
        if current_value < self.best_value:
            self.best_value = current_value
            self.best_position = [route[:] for route in self.routes]  # Deep copy to avoid reference issues

    def update_velocity(self, global_best_routes, inertia_weight=1.5, cognitive_weight=0.2, social_weight=0.2):
        for i in range(len(self.routes)):
            for j in range(len(self.routes[i])):
                if j < len(global_best_routes[i]):  # Ensure indices are within bounds
                    r1, r2 = np.random.rand(), np.random.rand()
                    cognitive_component = cognitive_weight * r1 * (self.best_position[i][j] - self.routes[i][j])
                    social_component = social_weight * r2 * (global_best_routes[i][j] - self.routes[i][j])
                    self.velocity[i][j] = inertia_weight * self.velocity[i][j] + cognitive_component + social_component

    def move(self):
        for i in range(len(self.routes)):
            for j in range(len(self.routes[i])):
                # Update positions, keep within bounds using modulo to stay within customer range
                self.routes[i][j] = int((self.routes[i][j] + self.velocity[i][j]) % (self.num_customers + 1))

def pso_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_particles, max_iterations):
    particles = [Particle(num_customers, num_vehicles, capacity, customer_demands, dist_matrix) for _ in range(num_particles)]
    global_best_routes = min(particles, key=lambda p: p.best_value).best_position
    global_best_value = vrp_cost(global_best_routes, dist_matrix)

    for iteration in range(max_iterations):
        for particle in particles:
            particle.update_personal_best()
            particle.update_velocity(global_best_routes)
            particle.move()

        current_global_best = min(particles, key=lambda p: p.best_value)
        if current_global_best.best_value < global_best_value:
            global_best_routes = [route[:] for route in current_global_best.best_position]  # Deep copy
            global_best_value = current_global_best.best_value

    return global_best_routes, global_best_value

# Test PSO and EHO on VRP
def test_pso_vs_eho_on_vrp():
    num_customers = 20  # Number of customers
    num_vehicles = 5     # Number of vehicles
    capacity = 50        # Vehicle capacity
    max_iterations = 100 # Maximum iterations
    num_particles = 30   # Number of particles for PSO
    num_elephants = 30   # Number of elephants for EHO
    num_herds = 5        # Number of herds for EHO

    # Generate random customer demands
    customer_demands = np.random.randint(1, 10, num_customers + 1)  # Depot has zero demand
    customer_demands[0] = 0  # Depot demand

    # Generate random customers and calculate distance matrix
    customers = generate_customers(num_customers)
    dist_matrix = calc_distance_matrix(customers)

    print("Testing PSO on VRP...")
    start_time = time.time()
    best_routes_pso, best_value_pso = pso_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_particles, max_iterations)
    pso_time = time.time() - start_time
    print(f"PSO Best Value: {best_value_pso}, Execution Time: {pso_time:.5f} seconds")

    print("\nTesting EHO on VRP...")
    start_time = time.time()
    best_routes_eho, best_value_eho = eho_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_elephants, num_herds, max_iterations)
    eho_time = time.time() - start_time
    print(f"EHO Best Value: {best_value_eho}, Execution Time: {eho_time:.5f} seconds")

# Run the comparison between PSO and EHO on VRP
test_pso_vs_eho_on_vrp()
