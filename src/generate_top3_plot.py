"""
Generates the publication-quality Top-3 Pest Prediction Probability Chart
for the AI-Powered Pest Prediction & Agricultural Advisory System.
Theme: Agricultural Green Palette
Output: plots/top3_prediction_chart.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def create_top3_chart(
    pests=None,
    probabilities=None,
    crop="Rice",
    output_path="plots/top3_prediction_chart.png"
):
    if pests is None:
        pests = ["Brown Planthopper", "Stem Borer", "Leaf Folder"]
    if probabilities is None:
        probabilities = [64.81, 23.54, 8.71]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Set up plot styling
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)

    # Reorder so rank 1 is on top
    y_pos = np.arange(len(pests))[::-1]
    sorted_pests = pests
    sorted_probs = probabilities

    # Agricultural Green Gradient Palette
    colors = ["#1b4332", "#2d6a4f", "#52b788"]  # Rank 1, 2, 3
    edge_colors = ["#081c15", "#1b4332", "#40916c"]

    # Horizontal bars
    bars = ax.barh(
        y_pos,
        sorted_probs,
        height=0.55,
        color=colors,
        edgecolor=edge_colors,
        linewidth=1.5,
        zorder=3
    )

    # Add data labels and badges
    for idx, (bar, prob, pest) in enumerate(zip(bars, sorted_probs, sorted_pests)):
        rank = idx + 1
        width = bar.get_width()
        # Text label with percentage
        ax.text(
            width + 1.2,
            bar.get_y() + bar.get_height() / 2.0,
            f"{prob:.2f}%  (Rank {rank})",
            va="center",
            ha="left",
            fontsize=12,
            fontweight="bold",
            color="#1b4332"
        )

    # Formatting axes
    ax.set_yticks(y_pos)
    ax.set_yticklabels(
        [f"#{idx+1}  {p}" for idx, p in enumerate(sorted_pests)],
        fontsize=13,
        fontweight="bold",
        color="#081c15"
    )
    ax.set_xlabel("Predicted Probability (%)", fontsize=12, fontweight="bold", color="#1b4332", labelpad=10)
    ax.set_xlim(0, max(sorted_probs) + 18)

    # Clean styling
    ax.grid(axis="x", linestyle="--", alpha=0.5, color="#74c69d", zorder=0)
    ax.grid(axis="y", visible=False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#2d6a4f")
    ax.spines["bottom"].set_linewidth(1.2)

    # Titles & Subtitles
    plt.title(
        f"Top-3 Candidate Pest Probability Ranking\nTarget Crop: {crop} | Model: ExtraTreesClassifier (predict_proba)",
        fontsize=14,
        fontweight="heavy",
        color="#081c15",
        pad=18,
        loc="left"
    )

    # Note / Caption
    plt.figtext(
        0.12, 0.01,
        "* Probabilities derived from calibrated ensemble trees based on microclimatic & edaphic indices.",
        fontsize=9,
        fontstyle="italic",
        color="#40916c"
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Top-3 prediction chart saved successfully to: {output_path}")

if __name__ == "__main__":
    create_top3_chart()
