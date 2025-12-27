#!/usr/bin/env python3
"""
Ping data analysis script
For analyzing long-term ping test data
"""

import re
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.dates as mdates

def create_result_directory():
    """Create result directory if it doesn't exist"""
    result_dir = 'result'
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    return result_dir

def parse_ping_data(filename):
    """
    Parse ping data file, extract timestamps, sequence numbers, and RTTs
    Returns: (timestamps list, sequences list, RTTs list)
    """
    timestamps = []
    sequences = []
    rtts = []
    
    # Regex pattern to match: [1766829706.448415] 64 bytes from 41.186.255.86: icmp_seq=1 ttl=63 time=388 ms
    pattern = re.compile(r'^\[(\d+\.\d+)\].*icmp_seq=(\d+).*time=([\d\.]+) ms')
    
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            match = pattern.match(line.strip())
            if match:
                timestamp = float(match.group(1))  # Unix timestamp (seconds.microseconds)
                seq = int(match.group(2))          # Sequence number
                rtt = float(match.group(3))        # RTT (milliseconds)
                
                timestamps.append(timestamp)
                sequences.append(seq)
                rtts.append(rtt)
            elif line.strip() and not line.startswith('PING') and not line.startswith('---'):
                print(f"Warning: Line {line_num} cannot be parsed: {line.strip()}")
    
    return timestamps, sequences, rtts

def calculate_delivery_stats(sequences):
    """
    Calculate delivery statistics
    Returns: dictionary containing various statistics
    """
    if not sequences:
        return {}
    
    total_received = len(sequences)
    # Assume sequence numbers start from 1 and are continuous, max sequence number is total sent
    max_seq = max(sequences)
    total_sent = max_seq  # Simplified assumption
    
    # Overall delivery rate
    delivery_rate = total_received / total_sent if total_sent > 0 else 0
    
    # Find all received sequence numbers
    received_set = set(sequences)
    
    # Find missing sequence numbers
    missing_sequences = []
    for seq in range(1, max_seq + 1):
        if seq not in received_set:
            missing_sequences.append(seq)
    
    # Calculate longest consecutive success and loss streaks
    max_consecutive_success = 0
    max_consecutive_loss = 0
    current_success = 0
    current_loss = 0
    
    for seq in range(1, max_seq + 1):
        if seq in received_set:
            current_success += 1
            current_loss = 0
            max_consecutive_success = max(max_consecutive_success, current_success)
        else:
            current_loss += 1
            current_success = 0
            max_consecutive_loss = max(max_consecutive_loss, current_loss)
    
    # Calculate conditional delivery rates
    # 1. Probability that packet N+1 succeeds given packet N succeeded
    # 2. Probability that packet N+1 succeeds given packet N failed
    
    # Build status array (1: success, 0: failure)
    status = [1 if seq in received_set else 0 for seq in range(1, max_seq + 1)]
    
    count_success_to_success = 0
    count_success_transitions = 0
    count_loss_to_success = 0
    count_loss_transitions = 0
    
    for i in range(len(status) - 1):
        if status[i] == 1:  # Current success
            count_success_transitions += 1
            if status[i + 1] == 1:  # Next also success
                count_success_to_success += 1
        else:  # Current failure
            count_loss_transitions += 1
            if status[i + 1] == 1:  # Next success
                count_loss_to_success += 1
    
    prob_success_given_success = (count_success_to_success / count_success_transitions 
                                  if count_success_transitions > 0 else 0)
    prob_success_given_loss = (count_loss_to_success / count_loss_transitions 
                               if count_loss_transitions > 0 else 0)
    
    return {
        'total_sent': total_sent,
        'total_received': total_received,
        'delivery_rate': delivery_rate,
        'missing_sequences': missing_sequences,
        'max_consecutive_success': max_consecutive_success,
        'max_consecutive_loss': max_consecutive_loss,
        'prob_success_given_success': prob_success_given_success,
        'prob_success_given_loss': prob_success_given_loss,
        'status_array': status
    }

def calculate_rtt_stats(rtts):
    """
    Calculate RTT statistics
    """
    if not rtts:
        return {}
    
    rtt_array = np.array(rtts)
    
    return {
        'min_rtt': np.min(rtt_array),
        'max_rtt': np.max(rtt_array),
        'mean_rtt': np.mean(rtt_array),
        'median_rtt': np.median(rtt_array),
        'std_rtt': np.std(rtt_array),
        'percentile_95': np.percentile(rtt_array, 95),
        'percentile_99': np.percentile(rtt_array, 99),
        'all_rtts': rtt_array
    }

def moving_average(data, window_size):
    """Calculate moving average using convolution"""
    weights = np.ones(window_size) / window_size
    return np.convolve(data, weights, mode='valid')

def plot_rtt_vs_time(timestamps, rtts, result_dir, filename_prefix="analysis"):
    """
    Plot RTT vs time
    """
    # Convert Unix timestamps to datetime objects
    times = [datetime.fromtimestamp(ts) for ts in timestamps]
    
    plt.figure(figsize=(14, 6))
    plt.plot(times, rtts, 'b-', alpha=0.7, linewidth=0.5, label='RTT')
    
    # Add moving average line (window size = 100 samples)
    window_size = min(100, len(rtts) // 10)
    if window_size > 1:
        moving_avg = moving_average(rtts, window_size)
        # Adjust times for moving average (center aligned)
        if len(times) > len(moving_avg):
            offset = (len(times) - len(moving_avg)) // 2
            avg_times = times[offset:offset + len(moving_avg)]
            plt.plot(avg_times, moving_avg, 'r-', linewidth=1.5, label=f'{window_size}-point moving average')
    
    plt.xlabel('Time (HH:MM)', fontsize=12)
    plt.ylabel('RTT (ms)', fontsize=12)
    plt.title('RTT vs Time', fontsize=14)
    
    # Set x-axis time format
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate()
    
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, f'{filename_prefix}_rtt_vs_time.png'), dpi=300)
    plt.show()

def plot_rtt_distribution(rtts, result_dir, filename_prefix="analysis"):
    """
    Plot RTT distribution histogram and CDF
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Histogram
    n, bins, patches = axes[0].hist(rtts, bins=50, alpha=0.7, edgecolor='black', density=True)
    axes[0].set_xlabel('RTT (ms)', fontsize=12)
    axes[0].set_ylabel('Probability Density', fontsize=12)
    axes[0].set_title('RTT Distribution Histogram', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    
    # Add statistics text
    stats_text = f'Mean: {np.mean(rtts):.2f} ms\nStd Dev: {np.std(rtts):.2f} ms\nMin: {np.min(rtts):.2f} ms\nMax: {np.max(rtts):.2f} ms'
    axes[0].text(0.02, 0.98, stats_text, transform=axes[0].transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Cumulative Distribution Function (CDF)
    sorted_rtts = np.sort(rtts)
    cdf = np.arange(1, len(sorted_rtts) + 1) / len(sorted_rtts)
    
    axes[1].plot(sorted_rtts, cdf, 'r-', linewidth=2)
    axes[1].set_xlabel('RTT (ms)', fontsize=12)
    axes[1].set_ylabel('Cumulative Probability', fontsize=12)
    axes[1].set_title('RTT Cumulative Distribution Function', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    
    # Mark key percentile points
    for percentile in [50, 90, 95, 99]:
        value = np.percentile(rtts, percentile)
        axes[1].axvline(x=value, color='gray', linestyle='--', alpha=0.5)
        axes[1].text(value, 0.05, f'{percentile}%: {value:.1f}ms', 
                    rotation=90, verticalalignment='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, f'{filename_prefix}_rtt_distribution.png'), dpi=300)
    plt.show()

def plot_rtt_correlation(rtts, result_dir, filename_prefix="analysis"):
    """
    Plot correlation between consecutive RTTs
    """
    if len(rtts) < 2:
        print("Insufficient data to calculate correlation")
        return
    
    # Create consecutive RTT pairs
    x = rtts[:-1]  # RTT of ping #N
    y = rtts[1:]   # RTT of ping #N+1
    
    plt.figure(figsize=(10, 8))
    plt.scatter(x, y, alpha=0.5, s=10, c='blue')
    
    # Add trend line
    if len(x) > 1:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_range = np.linspace(min(x), max(x), 100)
        plt.plot(x_range, p(x_range), 'r-', linewidth=2, label=f'Trend line: y={z[0]:.3f}x+{z[1]:.3f}')
    
    # Add diagonal line (y=x reference)
    min_val = min(min(x), min(y))
    max_val = max(max(x), max(y))
    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='y=x')
    
    plt.xlabel('RTT of Ping #N (ms)', fontsize=12)
    plt.ylabel('RTT of Ping #N+1 (ms)', fontsize=12)
    plt.title('Correlation Between Consecutive RTTs', fontsize=14)
    
    # Calculate correlation coefficient
    correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0
    plt.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
             transform=plt.gca().transAxes, fontsize=12,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, f'{filename_prefix}_rtt_correlation.png'), dpi=300)
    plt.show()

def plot_delivery_pattern(status_array, result_dir, filename_prefix="analysis"):
    """
    Plot delivery pattern (success/failure sequence)
    """
    plt.figure(figsize=(14, 3))
    
    # Convert status array to colors
    colors = ['red' if s == 0 else 'green' for s in status_array]
    
    # Create a bar for each sequence number
    x = range(1, len(status_array) + 1)
    y = [1] * len(status_array)
    
    plt.bar(x, y, color=colors, width=1.0, edgecolor='none')
    plt.xlabel('Sequence Number', fontsize=12)
    plt.ylabel('Delivery Status', fontsize=12)
    plt.title('Packet Delivery Pattern (Green: Success, Red: Loss)', fontsize=14)
    
    # Set y-axis
    plt.yticks([0.5], [''])
    
    plt.xlim(0.5, len(status_array) + 0.5)
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, f'{filename_prefix}_delivery_pattern.png'), dpi=300)
    plt.show()

def generate_report(delivery_stats, rtt_stats, timestamps, sequences, rtts):
    """
    Generate analysis report
    """
    report = []
    report.append("=" * 60)
    report.append("PING DATA ANALYSIS REPORT")
    report.append("=" * 60)
    report.append("")
    
    # Basic statistics
    report.append("1. BASIC STATISTICS")
    report.append(f"   Total packets sent: {delivery_stats['total_sent']}")
    report.append(f"   Total packets received: {delivery_stats['total_received']}")
    report.append(f"   Overall delivery rate: {delivery_stats['delivery_rate']:.4f} ({delivery_stats['delivery_rate']*100:.2f}%)")
    report.append(f"   Packets lost: {delivery_stats['total_sent'] - delivery_stats['total_received']}")
    report.append("")
    
    # Streak statistics
    report.append("2. STREAK STATISTICS")
    report.append(f"   Longest consecutive success streak: {delivery_stats['max_consecutive_success']} packets")
    report.append(f"   Longest consecutive loss streak: {delivery_stats['max_consecutive_loss']} packets")
    report.append("")
    
    # Conditional delivery rates
    report.append("3. CONDITIONAL DELIVERY RATES")
    report.append(f"   Probability of success given previous success: {delivery_stats['prob_success_given_success']:.4f}")
    report.append(f"   Probability of success given previous loss: {delivery_stats['prob_success_given_loss']:.4f}")
    report.append("")
    
    # Loss pattern analysis
    unconditional_rate = delivery_stats['delivery_rate']
    cond_success = delivery_stats['prob_success_given_success']
    cond_loss = delivery_stats['prob_success_given_loss']
    
    report.append("4. LOSS PATTERN ANALYSIS")
    if cond_success > unconditional_rate and cond_loss < unconditional_rate:
        report.append("   Conclusion: Loss shows bursty pattern")
        report.append("   - Success is more likely to be followed by success")
        report.append("   - Loss is more likely to be followed by loss")
    elif abs(cond_success - unconditional_rate) < 0.05 and abs(cond_loss - unconditional_rate) < 0.05:
        report.append("   Conclusion: Loss is mostly independent")
        report.append("   - Previous packet outcome has little effect on the next")
    else:
        report.append("   Conclusion: Loss pattern is complex with no clear trend")
    report.append("")
    
    # RTT statistics
    report.append("5. RTT STATISTICS")
    report.append(f"   Minimum RTT: {rtt_stats['min_rtt']:.2f} ms")
    report.append(f"   Maximum RTT: {rtt_stats['max_rtt']:.2f} ms")
    report.append(f"   Mean RTT: {rtt_stats['mean_rtt']:.2f} ms")
    report.append(f"   Median RTT: {rtt_stats['median_rtt']:.2f} ms")
    report.append(f"   RTT Standard Deviation: {rtt_stats['std_rtt']:.2f} ms")
    report.append(f"   95th percentile RTT: {rtt_stats['percentile_95']:.2f} ms")
    report.append(f"   99th percentile RTT: {rtt_stats['percentile_99']:.2f} ms")
    report.append("")
    
    # Experiment time information
    if timestamps:
        start_time = datetime.fromtimestamp(min(timestamps))
        end_time = datetime.fromtimestamp(max(timestamps))
        duration = end_time - start_time
        report.append("6. EXPERIMENT TIME INFORMATION")
        report.append(f"   Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"   End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"   Duration: {duration}")
        report.append(f"   Average send interval: {duration.total_seconds() / delivery_stats['total_sent']:.2f} seconds/packet")
    
    return "\n".join(report)

def main():
    # Create result directory
    result_dir = create_result_directory()
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python analyze_ping.py <data_file> [output_prefix]")
        print("Example: python analyze_ping.py data.txt analysis")
        sys.exit(1)
    
    filename = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "analysis"
    
    print(f"Analyzing file: {filename}")
    
    # Parse data
    print("1. Parsing data...")
    timestamps, sequences, rtts = parse_ping_data(filename)
    
    if not sequences:
        print("Error: No valid data found")
        sys.exit(1)
    
    print(f"   Parsed {len(sequences)} packets")
    
    # Calculate statistics
    print("2. Calculating statistics...")
    delivery_stats = calculate_delivery_stats(sequences)
    rtt_stats = calculate_rtt_stats(rtts)
    
    # Generate report
    print("3. Generating analysis report...")
    report = generate_report(delivery_stats, rtt_stats, timestamps, sequences, rtts)
    print(report)
    
    # Save report to file
    report_file = os.path.join(result_dir, f'{output_prefix}_report.txt')
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Generate plots
    print("4. Generating plots...")
    
    # RTT vs time
    print("   Generating RTT vs time plot...")
    plot_rtt_vs_time(timestamps, rtts, result_dir, output_prefix)
    
    # RTT distribution
    print("   Generating RTT distribution plot...")
    plot_rtt_distribution(rtts, result_dir, output_prefix)
    
    # Consecutive RTT correlation
    print("   Generating consecutive RTT correlation plot...")
    plot_rtt_correlation(rtts, result_dir, output_prefix)
    
    # Delivery pattern
    print("   Generating delivery pattern plot...")
    plot_delivery_pattern(delivery_stats['status_array'], result_dir, output_prefix)
    
    print("\nAnalysis completed!")
    print(f"Report saved to: {report_file}")
    print(f"Plots saved to: {result_dir}/{output_prefix}_*.png")

if __name__ == "__main__":
    main()