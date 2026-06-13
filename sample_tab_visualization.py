"""
Sample Guitar Tab Visualization
Demonstrates how the plot_tab() function from visualize.py works with sample data
This matches the actual implementation in src/visualize.py
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

def create_sample_tab_visualization(note_resolution=16):
    """
    Creates a sample guitar tab showing how the plot_tab() function works.
    Matches the actual implementation from visualize.py
    
    Args:
        note_resolution: number representing note subdivision (16 = 16th notes)
    """
    # Color scheme from visualize.py - different colors per string AND fret
    pitch_style_list = np.array([
        ["#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", 
         "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999"],
        ["#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300",
         "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000"],
        ["#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999",
         "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900"],
        ["#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000",
         "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC"],
        ["#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900",
         "#339900", "#006633", "#009999", "#003399", "#3300CC", "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300"],
        ["#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999", "#003399", "#3300CC", 
         "#9900CC", "#CC0099", "#000000", "#CC0000", "#993300", "#FF6600", "#CC9900", "#339900", "#006633", "#009999"]
    ])
    
    # Create sample tab data: shape (time_steps, 6_strings, 21_frets)
    # Indices 0-19 = fret numbers, index 20 = "not played" marker
    tab_length = 64
    tab = np.zeros((tab_length, 6, 21), dtype=float)
    
    # Mark all positions as "not played" initially by setting index 20 to 1
    tab[:, :, 20] = 1.0
    
    # Add sample note events: (time, string, fret)
    sample_notes = [
        (2, 0, 5),    # E string, fret 5
        (6, 1, 3),    # A string, fret 3
        (10, 2, 7),   # D string, fret 7
        (14, 3, 5),   # G string, fret 5
        (18, 0, 8),   # E string, fret 8
        (22, 4, 0),   # B string, open (fret 0)
        (26, 2, 9),   # D string, fret 9
        (30, 5, 3),   # low E string, fret 3
        (34, 1, 5),   # A string, fret 5
        (38, 0, 12),  # E string, fret 12
        (42, 3, 7),   # G string, fret 7
        (46, 4, 2),   # B string, fret 2
        (50, 2, 5),   # D string, fret 5
        (54, 5, 5),   # low E string, fret 5
        (58, 1, 7),   # A string, fret 7
    ]
    
    # Set the tab data (one-hot encoding)
    for time, string, fret in sample_notes:
        tab[time, string, :] = 0  # Clear all values first
        tab[time, string, fret] = 1  # Set the correct fret to 1
    
    # Now plot using the actual plot_tab() logic
    plt.figure(figsize=(14, 5))
    
    # Draw all 6 horizontal lines for strings at once
    plt.hlines(y=[0, 1, 2, 3, 4, 5], xmin=0, xmax=tab_length-1, colors='k', lw=0.15, zorder=0)
    
    # Draw vertical gridlines
    for time in range(len(tab)):
        if time % note_resolution == 0:  # Bar lines (thick)
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.3, zorder=0)
        elif time % 4 == 0:  # Beat lines (medium)
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.15, zorder=0)
        else:  # Subdivision lines (thin, dotted)
            plt.vlines(x=time, ymin=0, ymax=5, colors='k', lw=0.1, ls='dotted', zorder=0)
    
    # Add final bar line
    plt.vlines(x=len(tab), ymin=0, ymax=5, colors='k', lw=0.3, zorder=0)
    
    # Plot fret numbers using argmax (same as actual implementation)
    for time in range(len(tab)):
        for string in range(6):
            fret = np.argmax(tab[time, string])  # Get fret with highest value
            if fret != 20:  # 20 means "not played"
                color = pitch_style_list[string, fret]  # Get color based on string AND fret
                plt.scatter(time, string, s=50, marker=f"${fret}$", 
                           color=color, linewidths=1, zorder=5)
    
    # Set x-axis ticks to show bar numbers
    bar_positions = [i for i in range(0, len(tab)) if i % note_resolution == 0]
    bar_labels = [i // note_resolution for i in bar_positions]
    plt.xticks(bar_positions, labels=bar_labels)
    
    # Set y-axis ticks to show string names
    plt.yticks(np.arange(6), ('E', 'A', 'D', 'G', 'B', 'e'))
    
    # Set axis limits
    plt.ylim(-0.5, 5.5)
    
    # Labels
    plt.xlabel('Bar number')
    plt.ylabel('Guitar String')
    plt.title('Sample Guitar Tab Visualization (matching visualize.py plot_tab())')
    
    plt.tight_layout()
    plt.savefig('/Users/aarjan/Desktop/Tab-estimator-master/sample_tab_output.png', dpi=150, bbox_inches='tight')
    print("✓ Sample tab visualization saved to: sample_tab_output.png")
    plt.close()

if __name__ == "__main__":
    create_sample_tab_visualization()
