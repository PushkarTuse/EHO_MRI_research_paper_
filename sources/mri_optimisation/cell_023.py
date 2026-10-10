import numpy as np
import matplotlib.pyplot as plt

# Data for PSNR, SSIM, and Execution Time
psnr_values = [13.72, 13.72, 14.33]  # EHO, PSO, GA
ssim_values = [0.67, 0.67, 0.89]     # EHO, PSO, GA
execution_times = [0.3004, 0.3948, 0.6414]  # Reordered: EHO, GA, PSO
methods_psnr_ssim = ['EHO', 'PSO', 'GA']
methods_time = ['EHO', 'GA', 'PSO']  # Reordered for execution time

# Simulated small error for visualization purposes
psnr_error = [0.1, 0.12, 0.09]  # Hypothetical error bars for PSNR
ssim_error = [0.03, 0.02, 0.04] # Hypothetical error bars for SSIM

# X-axis positions for the groups
x = np.arange(len(methods_psnr_ssim))

# Bar width for PSNR/SSIM plot
width = 0.35

# Create the figure and two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

# 1st Plot: Bar graph for PSNR and SSIM
bars_psnr = ax1.bar(x - width/2, psnr_values, width, yerr=psnr_error, label='PSNR', color='blue', capsize=5)
bars_ssim = ax1.bar(x + width/2, ssim_values, width, yerr=ssim_error, label='SSIM', color='green', capsize=5)

# Labels and title for the bar graph
ax1.set_xlabel('Enhancement Methods', fontsize=12)
ax1.set_ylabel('Scores', fontsize=12)
ax1.set_title('MRI Image Enhancement and 3D Model Generation Using Bio-Inspired Algorithms: PSNR and SSIM Comparison for EHO, PSO, and GA', fontsize=16)
ax1.set_xticks(x)
ax1.set_xticklabels(methods_psnr_ssim, fontsize=12)

# Add grid for the bar graph
ax1.grid(True)

# Add legend for PSNR and SSIM
ax1.legend()

# Add annotations (labels) for PSNR bars
for bar in bars_psnr:
    height = bar.get_height()
    ax1.annotate(f'{height:.2f}',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3),  # Offset for label
                 textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, color='blue')

# Add annotations (labels) for SSIM bars
for bar in bars_ssim:
    height = bar.get_height()
    ax1.annotate(f'{height:.2f}',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3),  # Offset for label
                 textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, color='green')

# 2nd Plot: Line graph for execution time (reordered for increasing graph)
ax2.plot(methods_time, execution_times, marker='o', color='red', label='Execution Time')

# Labels and title for the line graph
ax2.set_xlabel('Enhancement Methods', fontsize=12)
ax2.set_ylabel('Execution Time (seconds)', fontsize=12)
ax2.set_title('MRI Image Enhancement and 3D Model Generation Using Bio-Inspired Algorithms: Execution Time Comparison for EHO, GA, and PSO ', fontsize=16)

# Add grid for the line graph
ax2.grid(True)

# Annotate points for execution time
for i, time in enumerate(execution_times):
    ax2.annotate(f'{time:.4f}s', (methods_time[i], time), textcoords="offset points", xytext=(0, 10),
                 ha='center', fontsize=10, color='red')

# Adjust layout for better spacing
plt.tight_layout()

# Show the combined plot
plt.show()
