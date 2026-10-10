import matplotlib.pyplot as plt

# Data for the chart
best_values = [5.09211346966514, 4.7997695069642425, 15.811119901981645, 19.943817220955953]  # Best values from your new results
algorithms = ['PSO', 'EHO', 'GA', 'ACO']  # Algorithm names

# Create the horizontal bar plot
plt.figure(figsize=(10, 6))
plt.barh(algorithms, best_values, color=['blue', 'red', 'green', 'orange'])

# Add labels and title
plt.xlabel('Best Value (Lower is Better)')
plt.ylabel('Algorithms')
plt.title('Best Values of Optimization Algorithms on Ackley Function')
plt.grid(True)

# Adding annotations to the bars
for index, value in enumerate(best_values):
    plt.text(value, index, f'{value:.2f}', va='center')

# Show the plot
plt.show()
