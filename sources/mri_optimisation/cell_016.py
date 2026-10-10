import matplotlib.pyplot as plt
import numpy as np

# Data from the results for execution time and best MSE
algorithms = ['PSO', 'EHO', 'GA', 'ACO']
execution_times = [4.93734, 1.67352, 3.27865, 1.26770]  # Execution times for PSO, EHO, GA, ACO
best_mse_values = [0.133565, 0.135149, 0.134779, 0.138497]  # Best MSE for PSO, EHO, GA, ACO

# Create a figure with two subplots: one for execution time and one for best MSE
fig, ax1 = plt.subplots(2, 1, figsize=(10, 8))

# Line plot for execution time
ax1[0].plot(algorithms, execution_times, marker='o', color='blue', label='Execution Time (seconds)')
ax1[0].set_title('Execution Time for PSO, EHO, GA, and ACO')
ax1[0].set_xlabel('Algorithms')
ax1[0].set_ylabel('Execution Time (seconds)')
ax1[0].grid(True)
for i, time in enumerate(execution_times):
    ax1[0].annotate(f'{time:.4f}s', (algorithms[i], time), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)

# Line plot for best MSE
ax1[1].plot(algorithms, best_mse_values, marker='o', color='red', label='Best MSE')
ax1[1].set_title('Best MSE for PSO, EHO, GA, and ACO')
ax1[1].set_xlabel('Algorithms')
ax1[1].set_ylabel('Best MSE')
ax1[1].grid(True)
for i, mse in enumerate(best_mse_values):
    ax1[1].annotate(f'{mse:.6f}', (algorithms[i], mse), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)

# Adjust layout for better spacing
plt.tight_layout()
plt.show()
