"""Plot actual recognizer sensitivity from bundled measured evidence.

Optional authoring dependency: matplotlib. This is a research figure, not a UI
mockup or a pronunciation-quality ranking.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    names = ["Piper · Danny low", "Kokoro · af_heart (ONNX)"]
    slugs = ["core-piper-danny", "core-kokoro-heart"]
    primary, alternate = [], []
    for slug in slugs:
        folder = ROOT / "examples" / slug
        for name, values in [("report.json", primary), ("alternate-asr-report.json", alternate)]:
            report = json.loads((folder / name).read_text(encoding="utf-8"))
            values.append(100 * report["research_protocol"]["scores"]["primary_target_retention"])
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(11.5, 4.7), facecolor="#fafaf8")
    ax.set_facecolor("#fafaf8")
    for i, (a, b) in enumerate(zip(primary, alternate)):
        ax.plot([b, a], [i, i], color="#bdc4cc", linewidth=3, zorder=1)
        ax.scatter(a, i, color="#28527a", s=95, zorder=3)
        ax.scatter(b, i, facecolors="#fafaf8", edgecolors="#28527a", linewidth=2, s=95, zorder=3)
        ax.text(a + 1.1, i, f"{a:.1f}%", va="center", fontsize=11, color="#17191c")
        ax.text(b - 1.1, i, f"{b:.1f}%", va="center", ha="right", fontsize=11, color="#59606a")
    ax.set_yticks(range(2), names)
    ax.invert_yaxis()
    ax.set_ylim(1.55, -.55)
    ax.set_xlim(0, 40)
    ax.set_xticks([0, 10, 20, 30, 40], ["0%", "10%", "20%", "30%", "40%"])
    ax.set_xlabel("Balanced primary-target retention · ASR proxy", labelpad=14)
    ax.xaxis.grid(True, color="#dfe2e6", linewidth=.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0, pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(.035, .925, "Same recordings. Different recognizers.", fontsize=21, fontweight="bold", color="#17191c")
    fig.text(.035, .868, "128 core cases per configuration · English · one generation per case", fontsize=11, color="#59606a")
    ax.legend(handles=[Line2D([0], [0], marker="o", linestyle="none", color="#28527a", markersize=8, label="Whisper small.en"),
                       Line2D([0], [0], marker="o", linestyle="none", color="#28527a", markerfacecolor="#fafaf8", markersize=8, label="Whisper base.en")],
              loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2, frameon=False, fontsize=10, borderaxespad=0)
    fig.text(.035, .06, "Measured lexical retention, not verified pronunciation accuracy. The connector is not a confidence interval.", fontsize=10, color="#59606a")
    fig.subplots_adjust(left=.245, right=.96, top=.715, bottom=.215)
    for extension in ("svg", "png"):
        fig.savefig(ROOT / "assets" / f"recognizer-sensitivity.{extension}", dpi=160, facecolor=fig.get_facecolor())
    svg = ROOT / "assets/recognizer-sensitivity.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)
    print("Plotted measured core-v1 recognizer sensitivity.")


if __name__ == "__main__":
    main()
