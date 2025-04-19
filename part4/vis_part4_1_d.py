import matplotlib.pyplot as plt
import mcPerfLogs
import os
import numpy as np
from collections import defaultdict

def main():
    # Define the configurations
    configs = {
        "experiment1Core1Threads": {"T": 2, "C": 1, "label": "Threads = 2, Cores = 1"},
        "experiment2Cores2Threads": {"T": 2, "C": 2, "label": "Threads = 2, Cores = 2"},
    }
    
    # Create a figure with two subplots
    fig, axs = plt.subplots(1, 2, figsize=(16, 8))
    
    # Colors for each configuration
    colors = ['blue', 'red']
    
    # Process each configuration
    for i, (exp_name, config) in enumerate(configs.items()):
        # Dictionary to store data points for each target QPS
        qps_data = defaultdict(list)
        latency_data = defaultdict(list)
        
        # Process each run
        for run in range(3):
            log_file = os.path.join(os.path.dirname(__file__), f"4_1_d_logs_run1", f"{exp_name}_run{run}.txt")
            mcperf_log = mcPerfLogs.McPerfLogs(log_file)
            data = mcperf_log.parse_log_file()
            
            # Sort data by target QPS to maintain order
            data.sort(key=lambda x: x["target"])
            
            # Extract QPS and p95 latency for each data point
            for point in data:
                qps = point["qps"]
                p95_latency = point["p95"]
                target = point["target"]
                
                qps_data[target].append(qps)
                latency_data[target].append(p95_latency)
            
        # Calculate average QPS and latency for each target QPS
        avg_qps = []
        avg_latency = []
        std_latency = []
        
        for target in sorted(qps_data.keys()):
            avg_qps.append(np.mean(qps_data[target]))
            avg_latency.append(np.mean(latency_data[target]))
            std_latency.append(np.std(latency_data[target]))
        
        # Plot the data with error bars and improved visibility
        axs[i].errorbar(avg_qps, avg_latency, yerr=std_latency, 
                    label=config["label"], color=colors[i], 
                    marker='o', linestyle='-', linewidth=1.5, markersize=5,
                    capsize=3, capthick=1, elinewidth=1)
        
        # Set labels and title for each subplot
        axs[i].set_xlabel('Achieved QPS', fontsize=12)
        axs[i].set_ylabel('95th Percentile Latency (μs)', fontsize=12)
        axs[i].set_title(f'Memcached Performance: {config["label"]}', fontsize=14)
        
        # Add grid with appropriate alpha
        axs[i].grid(True, linestyle='--', alpha=0.4, which='both')
        
        # Add legend
        axs[i].legend(fontsize=10, loc='upper left')
        
        # Add some padding to the axes
        axs[i].margins(x=0.02)
    
    # Add note about number of runs
    fig.text(0.5, 0.01, 'Note: Data averaged across 3 runs with error bars showing standard deviation', 
             ha='center', fontsize=10, style='italic')
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    
    # Save the figure with high DPI
    plt.savefig('memcached_performance_separate.png', dpi=300, bbox_inches='tight')
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    main()