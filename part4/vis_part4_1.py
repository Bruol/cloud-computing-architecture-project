import matplotlib.pyplot as plt
import mcPerfLogs
import os
import numpy as np
from collections import defaultdict

def main():
    # Define the configurations
    configs = {
        "experiment1": {"T": 1, "C": 1, "label": "Threads = 1, Cores = 1"},
        "experiment2": {"T": 1, "C": 2, "label": "Threads = 1, Cores = 2"},
        "experiment3": {"T": 2, "C": 1, "label": "Threads = 2, Cores = 1"},
        "experiment4": {"T": 2, "C": 2, "label": "Threads = 2, Cores = 2"}
    }
    
    # Create a figure with increased width
    plt.figure(figsize=(12, 8))
    
    # Colors for each configuration
    colors = ['blue', 'red', 'green', 'purple']
    

    # Process each configuration
    for i, (exp_name, config) in enumerate(configs.items()):
        # Dictionary to store data points for each target QPS
        qps_data = defaultdict(list)
        latency_data = defaultdict(list)
        
        # Process each run
        for run in range(3):
            log_file = os.path.join(os.path.dirname(__file__), f"logs_run1", f"{exp_name}_run{run}.txt")
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
        plt.errorbar(avg_qps, avg_latency, yerr=std_latency, 
                    label=config["label"], color=colors[i], 
                    marker='o', linestyle='-', linewidth=1.5, markersize=5,
                    capsize=3, capthick=1, elinewidth=1)
    
    # Set labels and title
    plt.xlabel('Achieved QPS', fontsize=12)
    plt.ylabel('95th Percentile Latency (μs)', fontsize=12)
    plt.title('Memcached Performance: 95th Percentile Latency vs. Achieved QPS', fontsize=14)
    
    # Set y-axis to log scale
    # plt.yscale('log')
    
    # Add grid with appropriate alpha for log scale
    plt.grid(True, linestyle='--', alpha=0.4, which='both')
    
    # Add legend
    plt.legend(fontsize=10, loc='upper left')
    
    # Add note about number of runs
    plt.figtext(0.5, 0.01, 'Note: Data averaged across 3 runs with error bars showing standard deviation', 
                ha='center', fontsize=10, style='italic')
    
    # Add some padding to the axes
    plt.margins(x=0.02)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    
    # Save the figure with high DPI
    plt.savefig('memcached_performance.png', dpi=300, bbox_inches='tight')
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    main()