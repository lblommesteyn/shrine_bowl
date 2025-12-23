import matplotlib
matplotlib.use('Agg') # Force headless mode
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Settings
output_dir = r"C:\Users\16476\OneDrive\Desktop\ss_sbc"
data_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\team_1_matched.csv"
analysis_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\full_analysis_results.csv"

def set_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Roboto', 'DejaVu Sans'],
        'figure.dpi': 300,
        'axes.facecolor': '#0d0d0d',
        'figure.facecolor': '#0d0d0d'
    })

class KalmanFilterCV:
    def __init__(self, dt=0.1, process_noise=0.5, measure_noise=0.1):
        self.dt = dt
        self.x = np.zeros((4, 1))
        # F: State Transition (Inertia Matrix)
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        # H: Measurement Function
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        self.P = np.eye(4) * 1000 
        self.Q = np.eye(4) * process_noise
        self.R = np.eye(2) * measure_noise

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x

    def update(self, z):
        z = np.array(z).reshape(2, 1)
        y = z - (self.H @ self.x) # Innovation
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + (K @ y)
        self.P = (np.eye(4) - (K @ self.H)) @ self.P
        return self.x, y

def create_kalman_viz():
    try:
        print("Loading data...")
        if not os.path.exists(data_path):
            print(f"Error: {data_path} not found.")
            return
            
        df_full = pd.read_csv(data_path)
        df_full['ts'] = pd.to_datetime(df_full['ts'])
        df_res = pd.read_csv(analysis_path)
        
        # Pick a rep with a SHARP cut to show Innovation
        # Loosen criteria to ensure we find *something*
        valid_reps = df_res[
            (df_res['Break_Angle'] > 100) & 
            (df_res['Route_Depth'] > 8)
        ].sort_values('Sep_at_Break', ascending=False)
    
        if valid_reps.empty:
            print("No ideal reps found, taking top separation rep.")
            valid_reps = df_res.sort_values('Sep_at_Break', ascending=False)
    
        best_rep = valid_reps.iloc[0]
        wr_name = best_rep['WR']
        break_time = pd.to_datetime(best_rep['Break_Time'])
        
        start_time = break_time - pd.Timedelta(seconds=1.5)
        end_time = break_time + pd.Timedelta(seconds=1.0)
        
        subset = df_full[
            (df_full['ts'] >= start_time) & 
            (df_full['ts'] <= end_time) & 
            (df_full['player_name'] == wr_name)
        ].sort_values('ts')
        
        measurements = subset[['x', 'y']].values
        
        kf = KalmanFilterCV(dt=0.1, process_noise=0.1, measure_noise=2.0)
        
        # Init
        if len(measurements) > 1:
            kf.x[0] = measurements[0][0]
            kf.x[1] = measurements[0][1]
            kf.x[2] = (measurements[1][0] - measurements[0][0]) / 0.1
            kf.x[3] = (measurements[1][1] - measurements[0][1]) / 0.1
        else:
            print("Not enough measurements in window.")
            return

        preds_x = []
        preds_y = []
        innov_pts = []
        
        for i, z in enumerate(measurements):
            pred_state = kf.x.copy()
            pred_next = kf.F @ pred_state
            preds_x.append(pred_next[0,0])
            preds_y.append(pred_next[1,0])
            
            _, y = kf.update(z)
            innov_mag = np.sqrt(y[0,0]**2 + y[1,0]**2)
            
            # Capture innovation lines -> reduce threshold to show more lines
            if innov_mag > 0.3:
                 innov_pts.append({
                     'start': (pred_next[0,0], pred_next[1,0]),
                     'end': (z[0], z[1]),
                     'mag': innov_mag
                 })
                 
            kf.predict()
    
        # Plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Field
        for x in range(int(subset['x'].min()), int(subset['x'].max()) + 5, 5):
            ax.axvline(x, color='#222', linewidth=1)
            
        # 1. Prediction (Inertia)
        ax.plot(preds_x, preds_y, color='white', linestyle='--', linewidth=2, alpha=0.5, label=r'Inertia ($F_k \hat{x}$)')
        
        # 2. Measurement (Reality)
        ax.plot(subset['x'], subset['y'], color='#00FFFF', linewidth=4, label=r'Reality ($z_k$)')
        
        # 3. Draw Innovation Lines (The Gap)
        for i, pt in enumerate(innov_pts):
            if i % 2 == 0: 
                ax.plot([pt['start'][0], pt['end'][0]], [pt['start'][1], pt['end'][1]], 
                        color='#FF00FF', linewidth=2, alpha=0.8)
    
        # Fake legend entry
        ax.plot([], [], color='#FF00FF', linewidth=2, label=r'Innovation ($\tilde{y}$)')
        
        # Annotation
        mid = len(innov_pts) // 2
        if mid < len(innov_pts):
            mx, my = innov_pts[mid]['end']
            px, py = innov_pts[mid]['start']
            ax.annotate(r"$\tilde{y}$", xy=(mx, my), xytext=(px, py), 
                        arrowprops=dict(arrowstyle="->", color="#FF00FF", lw=2),
                        color="#FF00FF", fontsize=16, fontweight='bold')
        
        ax.set_title("Kalman Filter: Quantifying The Break", fontsize=20, fontweight='bold', color='white', pad=20)
        ax.legend(loc='lower right', fontsize=12, facecolor='black', edgecolor='#444')
        ax.axis('off')
        
        plt.tight_layout()
        save_path = os.path.join(output_dir, "viz_kalman.png")
        plt.savefig(save_path, facecolor='#0d0d0d')
        print(f"Success: Saved to {save_path}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    set_style()
    create_kalman_viz()
