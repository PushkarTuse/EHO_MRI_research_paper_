import numpy as np
import random
import time
import matplotlib.pyplot as plt

# VRP cost function: total distance of the routes
def vrp_cost(routes, dist_matrix):
    total_cost = 0
    for route in routes:
        if route:  # If the route is not empty
            total_cost += dist_matrix[0][route[0]]  # From depot to the first customer
            for i in range(len(route) - 1):
                total_cost += dist_matrix[route[i]][route[i + 1]]  # Between customers
            total_cost += dist_matrix[route[-1]][0]  # From the last customer back to the depot
    return total_cost

# Generate random customers and calculate distance matrix
def generate_customers(num_customers):
    customers = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(num_customers + 1)]  # Including depot
    return customers

def calc_distance_matrix(customers):
    num_customers = len(customers)
    dist_matrix = np.zeros((num_customers, num_customers))
    for i in range(num_customers):
        for j in range(num_customers):
            dist_matrix[i][j] = np.linalg.norm(np.array(customers[i]) - np.array(customers[j]))
    return dist_matrix

# Function to visualize routes
def visualize_routes(customers, routes, title):
    depot = customers[0]

    plt.figure(figsize=(10, 10))

    # Plot depot
    plt.plot(depot[0], depot[1], 'ro', markersize=10, label='Depot')

    # Plot customers
    customer_points = customers[1:]
    customer_x = [c[0] for c in customer_points]
    customer_y = [c[1] for c in customer_points]
    plt.scatter(customer_x, customer_y, c='blue', label='Customers')

    # Different colors for each vehicle route
    colors = ['green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'yellow', 'black']

    # Plot each route
    for i, route in enumerate(routes):
        route_customers = [customers[customer] for customer in route]
        route_customers.insert(0, depot)  # Start from depot
        route_customers.append(depot)  # Return to depot
        route_x = [r[0] for r in route_customers]
        route_y = [r[1] for r in route_customers]

        plt.plot(route_x, route_y, color=colors[i % len(colors)], marker='o', label=f'Vehicle {i+1} Route')

    plt.title(title)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.legend()
    plt.grid(True)
    plt.show()

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

    return global_best_routes, global_best_value, None

# Elephant Herding Optimization (EHO) for VRP
class Elephant:
    def __init__(self, num_customers, num_vehicles, capacity, customer_demands, dist_matrix):
        self.num_customers = num_customers
        self.num_vehicles = num_vehicles
        self.capacity = capacity
        self.customer_demands = customer_demands
        self.dist_matrix = dist_matrix
        self.routes = self.initialize_routes()
        self.fitness = vrp_cost(self.routes, self.dist_matrix)

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

    def update_position(self, herd_best_routes, global_best_routes, iteration, max_iterations, bounds):
        r = np.random.rand()
        inertia_weight = 0.9 - 0.5 * (iteration / max_iterations)  # Decreasing inertia weight
        new_routes = []

        for i in range(len(self.routes)):
            new_route = []
            for customer in self.routes[i]:
                if np.random.rand() < r:  # Move customer based on random factor
                    new_route.append(customer)
            for customer in herd_best_routes[i]:
                if customer not in new_route and len(new_route) < len(self.routes[i]):
                    new_route.append(customer)
            new_routes.append(new_route)

        # Update the new fitness and routes
        new_fitness = vrp_cost(new_routes, self.dist_matrix)
        if new_fitness < self.fitness:
            self.routes = new_routes
            self.fitness = new_fitness

def eho_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_elephants, num_herds, max_iterations):
    elephants = [Elephant(num_customers, num_vehicles, capacity, customer_demands, dist_matrix) for _ in range(num_elephants)]
    herds = np.array_split(elephants, num_herds)
    global_best_routes = min(elephants, key=lambda e: e.fitness).routes
    global_best_fitness = vrp_cost(global_best_routes, dist_matrix)

    for iteration in range(max_iterations):
        for herd in herds:
            herd_best_routes = min(herd, key=lambda e: e.fitness).routes
            for elephant in herd:
                elephant.update_position(herd_best_routes, global_best_routes, iteration, max_iterations, dist_matrix)

                current_global_best = min(elephants, key=lambda e: e.fitness)
        if current_global_best.fitness < global_best_fitness:
            global_best_routes = current_global_best.routes
            global_best_fitness = current_global_best.fitness

    return global_best_routes, global_best_fitness, None

# Test PSO and EHO on VRP and visualize the results
def test_pso_vs_eho_with_visualization():
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

    # Testing PSO
    print("Testing PSO on VRP...")
    best_routes_pso, best_value_pso, _ = pso_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_particles, max_iterations)
    print(f"PSO Best Value: {best_value_pso}")

    # Visualize PSO routes
    visualize_routes(customers, best_routes_pso, 'PSO - Vehicle Routing Solution')

    # Testing EHO
    print("\nTesting EHO on VRP...")
    best_routes_eho, best_value_eho, _ = eho_vrp(num_customers, num_vehicles, customer_demands, capacity, dist_matrix, num_elephants, num_herds, max_iterations)
    print(f"EHO Best Value: {best_value_eho}")

    # Visualize EHO routes
    visualize_routes(customers, best_routes_eho, 'EHO - Vehicle Routing Solution')

    # Create a bar graph to compare PSO and EHO best values
    algorithms = ['PSO', 'EHO']
    best_values = [best_value_pso, best_value_eho]

    plt.figure(figsize=(8, 6))
    plt.bar(algorithms, best_values, color=['blue', 'green'])

    # Adding labels and title
    plt.ylabel('Best Value (Total Distance)')
    plt.title('Comparison of PSO and EHO Best Values on VRP')

    # Show the values on top of the bars
    for i, value in enumerate(best_values):
        plt.text(i, value + 10, f'{value:.2f}', ha='center', va='bottom', fontsize=12)

    plt.show()

# Run the test with route visualization and bar graph
test_pso_vs_eho_with_visualization()

