import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"

def set_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans'],
        'figure.dpi': 300
    })

def create_methodology_flow():
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis('off')
    
    # Draw Pipeline Steps
    # Step 1: Input
    ax.add_patch(patches.FancyBboxPatch((0.5, 0.5), 2.5, 2, boxstyle="round,pad=0.1", fc='#E8F4F8', ec='#1f77b4', lw=2))
    plt.text(1.75, 1.8, "INPUT", ha='center', fontsize=12, fontweight='bold', color='#1f77b4')
    plt.text(1.75, 1.3, "Raw Tracking\n(x,y,t)\n246 Reps", ha='center', fontsize=10, color='black')
    
    # Arrow 1
    ax.arrow(3.2, 1.5, 0.8, 0, head_width=0.2, head_length=0.2, fc='gray', ec='gray')
    
    # Step 2: Processing
    ax.add_patch(patches.FancyBboxPatch((4.2, 0.5), 2.5, 2, boxstyle="round,pad=0.1", fc='#E8F4F8', ec='#1f77b4', lw=2))
    plt.text(5.45, 1.8, "PHYSICS", ha='center', fontsize=12, fontweight='bold', color='#1f77b4')
    plt.text(5.45, 1.3, "Event Detection\n(Cuts/Breaks)\nAlignment", ha='center', fontsize=10, color='black')
    
    # Arrow 2
    ax.arrow(6.9, 1.5, 0.8, 0, head_width=0.2, head_length=0.2, fc='gray', ec='gray')
    
    # Step 3: Output
    ax.add_patch(patches.FancyBboxPatch((7.9, 0.5), 1.8, 2, boxstyle="round,pad=0.1", fc='#1f77b4', ec='#1f77b4', lw=2))
    plt.text(8.8, 1.5, "WROE\nGRADE", ha='center', fontsize=14, fontweight='bold', color='white')
    
    plt.title("Methodology: The Metric Engine", fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_path = os.path.join(output_dir, "viz_methodology_flow.png")
    plt.savefig(save_path)
    print(f"Saved methodology flow to {save_path}")

def create_impact_visual():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 4)
    ax.axis('off')
    
    # Draw Impacts
    # 1. Drafting
    ax.add_patch(patches.Circle((2, 2), 1.5, fc='#f0f9e8', ec='#2ca02c', lw=2))
    plt.text(2, 2.3, "DRAFT", ha='center', fontsize=14, fontweight='bold', color='#2ca02c')
    plt.text(2, 1.7, "Uncover\nSeparators\n(scheme-indep)", ha='center', fontsize=10)
    
    # 2. Scouting
    ax.add_patch(patches.Circle((6, 2), 1.5, fc='#e8f4f8', ec='#1f77b4', lw=2))
    plt.text(6, 2.3, "SCOUT", ha='center', fontsize=14, fontweight='bold', color='#1f77b4')
    plt.text(6, 1.7, "Identify\nErasers\n(high burst)", ha='center', fontsize=10)
    
    # Connection
    plt.text(4, 2, "+", ha='center', fontsize=30, fontweight='bold', color='gray')
    
    plt.title("Strategic Impact: Double-Side Value", fontsize=16, fontweight='bold', y=1.05)
    plt.tight_layout()
    save_path = os.path.join(output_dir, "viz_impact.png")
    plt.savefig(save_path)
    print(f"Saved impact visual to {save_path}")

if __name__ == "__main__":
    set_style()
    create_methodology_flow()
    create_impact_visual()
